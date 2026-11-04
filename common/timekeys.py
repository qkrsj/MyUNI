# -*- coding: utf-8 -*-
"""날짜 · 시즌 키. 기준 시간대는 한국 시간(KST, UTC+9) 고정.

    하루   'YYYY-MM-DD'
    시즌   ISO 주차 'YYYY-Www'. 월요일 00:00 KST 에 바뀐다.

시즌 초기화는 표를 비우는 게 아니라 새 주차 키로 쌓는 방식이다.
그래서 따로 도는 배치가 필요 없고 지난 시즌 기록도 남는다.
"""
import datetime

KST = datetime.timezone(datetime.timedelta(hours=9))

SCHOOL_CHANGE_COOLDOWN_DAYS = 30


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def day_key(when=None):
    return (when or utcnow()).astimezone(KST).date().isoformat()


def week_key(when=None):
    year, week, _ = (when or utcnow()).astimezone(KST).isocalendar()
    return "%d-W%02d" % (year, week)
