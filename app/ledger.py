"""Append-only run ledger, idempotent actions, exceptions and the seller's message feed, in SQLite."""
import json
import sqlite3
import threading
import time
from datetime import date

from . import config

SCHEMA = """
create table if not exists ledger(id integer primary key, at real, actor text, kind text, detail text,
  ref text, tokens_in int default 0, tokens_out int default 0, cost real default 0, ms int default 0);
create table if not exists actions(id integer primary key, key text unique, exception_id int, type text,
  args text, decision text, state text, result text, created real, decided real, decided_by text);
create table if not exists exceptions(id integer primary key, opened real, type text, order_id text,
  title text, status text, story text);
create table if not exists messages(id integer primary key, at real, direction text, text text, action_id int);
"""


class Ledger:
    def __init__(self, path: str = config.DB_PATH):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.db.executescript(SCHEMA)
        try:  # databases created before the evidence column existed
            self.db.execute("alter table exceptions add column evidence text")
        except sqlite3.OperationalError:
            pass

    def reset(self):
        """Start a fresh run (the night simulator). Ledger rows stay so today's spend still counts toward the cap."""
        with self.lock:
            self.db.executescript("delete from actions; delete from exceptions; delete from messages;")
        self.log("executor", "run_start", "new night on the demo store")

    def run_rows(self, limit=150):
        start = self.q("select coalesce(max(id),0) m from ledger where kind='run_start'")[0]["m"]
        return self.q("select * from ledger where id>=? order by id desc limit ?", start, limit)

    def q(self, sql, *args):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def x(self, sql, *args) -> int:
        with self.lock:
            return self.db.execute(sql, args).lastrowid

    # ---- ledger
    def log(self, actor, kind, detail, ref="", tokens_in=0, tokens_out=0, cost=0.0, ms=0):
        return self.x("insert into ledger(at,actor,kind,detail,ref,tokens_in,tokens_out,cost,ms) values(?,?,?,?,?,?,?,?,?)",
                      time.time(), actor, kind, detail, ref, tokens_in, tokens_out, cost, ms)

    def spent_today(self) -> float:
        start = time.mktime(date.today().timetuple())
        return self.q("select coalesce(sum(cost),0) s from ledger where at>=?", start)[0]["s"]

    # ---- actions: one row per idempotency key, so a retried key never runs twice
    def claim(self, key, exception_id, type_, args, decision) -> dict | None:
        """Insert the action if its key is new; return the existing row if it is not."""
        old = self.q("select * from actions where key=?", key)
        if old:
            return old[0]
        self.x("insert into actions(key,exception_id,type,args,decision,state,created) values(?,?,?,?,?,?,?)",
               key, exception_id, type_, json.dumps(args, ensure_ascii=False), decision, "new", time.time())
        return None

    def action(self, key=None, id=None):
        rows = self.q("select * from actions where key=?", key) if key else self.q("select * from actions where id=?", id)
        return rows[0] if rows else None

    def set_action(self, key, state, result=None, decided_by=None):
        self.x("update actions set state=?, result=coalesce(?,result), decided=case when ? is null then decided else ? end, "
               "decided_by=coalesce(?,decided_by) where key=?",
               state, None if result is None else json.dumps(result, ensure_ascii=False), decided_by, time.time(), decided_by, key)

    def pending(self):
        return self.q("select * from actions where state='pending' order by id")

    # ---- exceptions and messages
    def open_exception(self, type_, order_id, title, evidence=None) -> int:
        return self.x("insert into exceptions(opened,type,order_id,title,status,story,evidence) values(?,?,?,?,?,?,?)",
                      time.time(), type_, order_id, title, "fixing", "", json.dumps(evidence, ensure_ascii=False) if evidence else None)

    def update_exception(self, id, status=None, story=None):
        self.x("update exceptions set status=coalesce(?,status), story=coalesce(?,story) where id=?", status, story, id)

    def say(self, direction, text, action_id=None):
        return self.x("insert into messages(at,direction,text,action_id) values(?,?,?,?)", time.time(), direction, text, action_id)
