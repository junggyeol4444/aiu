"""
action_decider.py - 행동 결정 모듈
현재 컨텍스트를 분석하여 AI가 취할 행동 유형을 결정합니다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger


class ActionType(str, Enum):
    """AI가 선택할 수 있는 행동 유형."""

    FREE_TALK = "free_talk"           # 자유 토크 (혼잣말, 잡담)
    CHAT_REPLY = "chat_reply"         # 채팅 반응 (특정 시청자에게 답변)
    TOPIC_CHANGE = "topic_change"     # 주제 전환
    REACTION = "reaction"             # 리액션 (웃기, 놀라기)
    ASK_VIEWERS = "ask_viewers"       # 시청자에게 질문 던지기
    ANNOUNCEMENT = "announcement"     # 공지/알림
    SILENCE = "silence"               # 자연스러운 침묵/쉼
    GREETING = "greeting"             # 인사 (환영, 퇴장)
    DONATION_REACT = "donation_react" # 후원 반응
    SUBSCRIBE_REACT = "subscribe_react"  # 구독/팔로우 반응


@dataclass
class Action:
    """결정된 행동 정보를 담는 데이터 클래스."""

    action_type: ActionType
    priority: int = 0                          # 높을수록 우선순위 높음
    target_user: Optional[str] = None          # 대상 시청자 (채팅 반응 시)
    trigger_message: Optional[str] = None      # 트리거가 된 채팅 메시지
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionDecider:
    """현재 상황을 판단하여 AI의 다음 행동을 결정하는 클래스."""

    # 상황이 없을 때 자유 토크 행동들의 가중치
    _DEFAULT_WEIGHTS: dict[ActionType, float] = {
        ActionType.FREE_TALK: 0.40,
        ActionType.TOPIC_CHANGE: 0.15,
        ActionType.REACTION: 0.10,
        ActionType.ASK_VIEWERS: 0.20,
        ActionType.ANNOUNCEMENT: 0.05,
        ActionType.SILENCE: 0.10,
    }

    def decide(self, context: dict[str, Any]) -> Action:
        """
        컨텍스트를 분석하여 다음 행동을 결정합니다.

        Args:
            context: perception 모듈이 생성한 현재 상황 컨텍스트

        Returns:
            결정된 Action 객체
        """
        # 1. 고우선순위 이벤트 우선 처리
        action = self._check_high_priority_events(context)
        if action:
            logger.debug(f"고우선순위 이벤트 행동 결정: {action.action_type}")
            return action

        # 2. 채팅 메시지가 있으면 답변 우선
        recent_chats = context.get("recent_chat", [])
        if recent_chats:
            latest_chat = recent_chats[-1]
            action = Action(
                action_type=ActionType.CHAT_REPLY,
                priority=5,
                target_user=latest_chat.get("username"),
                trigger_message=latest_chat.get("message"),
            )
            logger.debug(f"채팅 반응 결정: {action.target_user}")
            return action

        # 3. 특별 상황이 없으면 가중치 기반 랜덤 선택
        return self._weighted_random_action(context)

    def _check_high_priority_events(self, context: dict[str, Any]) -> Optional[Action]:
        """후원, 구독 등 고우선순위 이벤트를 확인합니다."""
        events = context.get("events", [])
        for event in events:
            event_type = event.get("type", "")

            if event_type == "donation":
                return Action(
                    action_type=ActionType.DONATION_REACT,
                    priority=10,
                    metadata=event,
                )
            if event_type in ("subscription", "follow"):
                return Action(
                    action_type=ActionType.SUBSCRIBE_REACT,
                    priority=9,
                    target_user=event.get("username"),
                    metadata=event,
                )
            if event_type == "stream_start":
                return Action(
                    action_type=ActionType.GREETING,
                    priority=10,
                    metadata=event,
                )

        return None

    def _weighted_random_action(self, context: dict[str, Any]) -> Action:
        """가중치 기반으로 랜덤하게 행동을 선택합니다."""
        weights = dict(self._DEFAULT_WEIGHTS)

        # 시청자 수에 따라 가중치 조정
        viewer_count = context.get("viewer_count", 0)
        if viewer_count == 0:
            # 시청자가 없으면 자유 토크 비중 높임
            weights[ActionType.FREE_TALK] = 0.60
            weights[ActionType.SILENCE] = 0.20

        action_types = list(weights.keys())
        weight_values = [weights[a] for a in action_types]

        chosen = random.choices(action_types, weights=weight_values, k=1)[0]
        return Action(action_type=chosen, priority=1)
