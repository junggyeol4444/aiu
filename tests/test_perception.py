"""
test_perception.py - 인지 엔진 모듈 단위 테스트
"""

from __future__ import annotations

import asyncio
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── ChatMessage 테스트 ─────────────────────────────────────────────

class TestChatMessage:
    """ChatMessage 클래스 테스트."""

    def test_to_dict(self) -> None:
        """ChatMessage.to_dict()가 올바른 딕셔너리를 반환하는지 테스트."""
        from src.perception.chat_listener import ChatMessage

        msg = ChatMessage(
            username="user1",
            message="안녕하세요",
            timestamp="2026-01-01T00:00:00",
            platform="youtube",
        )
        d = msg.to_dict()
        assert d["username"] == "user1"
        assert d["message"] == "안녕하세요"
        assert d["platform"] == "youtube"

    def test_default_values(self) -> None:
        """ChatMessage 기본값이 올바른지 테스트."""
        from src.perception.chat_listener import ChatMessage

        msg = ChatMessage(username="user", message="hello")
        assert msg.platform == "unknown"
        assert msg.badges == []
        assert msg.timestamp == ""


# ── ChatListener 테스트 ────────────────────────────────────────────

class TestChatListener:
    """ChatListener 클래스 테스트."""

    def test_initial_state(self) -> None:
        """초기 상태가 올바른지 테스트."""
        from src.perception.chat_listener import ChatListener

        listener = ChatListener({"active": "youtube"})
        assert listener.get_recent_messages() == []
        assert not listener._running

    def test_get_recent_messages_limit(self) -> None:
        """최근 메시지 개수 제한이 올바르게 동작하는지 테스트."""
        from src.perception.chat_listener import ChatListener, ChatMessage

        listener = ChatListener({"active": "youtube"})
        for i in range(10):
            listener._message_queue.append(ChatMessage(f"user{i}", f"msg{i}"))

        messages = listener.get_recent_messages(n=3)
        assert len(messages) == 3
        assert messages[-1]["username"] == "user9"

    def test_clear_queue(self) -> None:
        """큐 초기화가 올바르게 동작하는지 테스트."""
        from src.perception.chat_listener import ChatListener, ChatMessage

        listener = ChatListener({"active": "youtube"})
        listener._message_queue.append(ChatMessage("user", "msg"))
        listener.clear_queue()
        assert listener.get_recent_messages() == []


# ── EventDetector 테스트 ───────────────────────────────────────────

class TestEventDetector:
    """EventDetector 클래스 테스트."""

    def test_add_donation_event(self) -> None:
        """후원 이벤트 추가가 올바르게 동작하는지 테스트."""
        from src.perception.event_detector import EventDetector

        detector = EventDetector()
        detector.add_donation("sponsor", 10000, "응원합니다!")
        assert detector.has_events()

        events = detector.get_pending_events()
        assert len(events) == 1
        assert events[0]["type"] == "donation"
        assert events[0]["username"] == "sponsor"
        assert events[0]["amount"] == 10000

    def test_add_subscription_event(self) -> None:
        """구독 이벤트 추가가 올바르게 동작하는지 테스트."""
        from src.perception.event_detector import EventDetector

        detector = EventDetector()
        detector.add_subscription("newsubber", months=3)

        events = detector.get_pending_events()
        assert len(events) == 1
        assert events[0]["type"] == "subscription"
        assert events[0]["username"] == "newsubber"

    def test_get_pending_events_clears_queue(self) -> None:
        """이벤트 조회 후 큐가 비워지는지 테스트."""
        from src.perception.event_detector import EventDetector

        detector = EventDetector()
        detector.add_follow("follower1")
        assert detector.has_events()

        detector.get_pending_events()
        assert not detector.has_events()

    def test_stream_start_event(self) -> None:
        """방송 시작 이벤트가 올바르게 추가되는지 테스트."""
        from src.perception.event_detector import EventDetector

        detector = EventDetector()
        detector.signal_stream_start()

        events = detector.get_pending_events()
        assert len(events) == 1
        assert events[0]["type"] == "stream_start"


# ── ViewerTracker 테스트 ───────────────────────────────────────────

class TestViewerTracker:
    """ViewerTracker 클래스 테스트."""

    def test_initial_count(self) -> None:
        """초기 시청자 수가 0인지 테스트."""
        from src.perception.viewer_tracker import ViewerTracker

        tracker = ViewerTracker({"active": "youtube"})
        assert tracker.current_count == 0

    def test_change_status_stable(self) -> None:
        """안정적인 상태에서 'stable'을 반환하는지 테스트."""
        from src.perception.viewer_tracker import ViewerTracker

        tracker = ViewerTracker({"active": "youtube"})
        tracker._current_count = 100
        tracker._previous_count = 100
        assert tracker.get_change_status() == "stable"

    def test_change_status_surge(self) -> None:
        """시청자 급등 감지 테스트."""
        from src.perception.viewer_tracker import ViewerTracker

        tracker = ViewerTracker({"active": "youtube"})
        tracker._previous_count = 100
        tracker._current_count = 200  # 100% 증가
        assert tracker.get_change_status() == "surge"

    def test_change_status_drop(self) -> None:
        """시청자 급감 감지 테스트."""
        from src.perception.viewer_tracker import ViewerTracker

        tracker = ViewerTracker({"active": "youtube"})
        tracker._previous_count = 100
        tracker._current_count = 50  # 50% 감소
        assert tracker.get_change_status() == "drop"

    def test_change_status_no_previous(self) -> None:
        """이전 데이터가 없을 때 'stable'을 반환하는지 테스트."""
        from src.perception.viewer_tracker import ViewerTracker

        tracker = ViewerTracker({"active": "youtube"})
        tracker._previous_count = 0
        tracker._current_count = 100
        assert tracker.get_change_status() == "stable"
