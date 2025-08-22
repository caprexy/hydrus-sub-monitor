#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Any, Dict
import datetime


@dataclass
class Query:
    """Data model for a subscription query"""
    id: Optional[int]
    query_text: str
    human_name: str
    display_name: str
    last_check_time: int
    next_check_time: int
    next_check_status: str
    paused: bool
    dead: bool
    checking_now: bool
    can_check_now: bool
    checker_status: int
    file_velocity: List[Any]
    file_seed_cache_status: str
    last_file_time: int
    acknowledged: bool = False
    acknowledged_time: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Query':
        """Create Query instance from dictionary"""
        return cls(
            id=data.get('id'),
            query_text=data.get('query_text', ''),
            human_name=data.get('human_name', ''),
            display_name=data.get('display_name', ''),
            last_check_time=data.get('last_check_time', 0),
            next_check_time=data.get('next_check_time', 0),
            next_check_status=data.get('next_check_status', ''),
            paused=bool(data.get('paused', False)),
            dead=bool(data.get('dead', False)),
            checking_now=bool(data.get('checking_now', False)),
            can_check_now=bool(data.get('can_check_now', False)),
            checker_status=data.get('checker_status', 0),
            file_velocity=data.get('file_velocity', []),
            file_seed_cache_status=data.get('file_seed_cache_status', ''),
            last_file_time=data.get('last_file_time', 0),
            acknowledged=bool(data.get('acknowledged', False)),
            acknowledged_time=data.get('acknowledged_time', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Query instance to dictionary"""
        return {
            'id': self.id,
            'query_text': self.query_text,
            'human_name': self.human_name,
            'display_name': self.display_name,
            'last_check_time': self.last_check_time,
            'next_check_time': self.next_check_time,
            'next_check_status': self.next_check_status,
            'paused': self.paused,
            'dead': self.dead,
            'checking_now': self.checking_now,
            'can_check_now': self.can_check_now,
            'checker_status': self.checker_status,
            'file_velocity': self.file_velocity,
            'file_seed_cache_status': self.file_seed_cache_status,
            'last_file_time': self.last_file_time,
            'acknowledged': self.acknowledged,
            'acknowledged_time': self.acknowledged_time
        }
    
    @property
    def display_text(self) -> str:
        """Get display text for the query"""
        return self.human_name or self.query_text
    
    @property
    def is_expired_acknowledgment(self) -> bool:
        """Check if acknowledgment has expired"""
        if not self.acknowledged or self.acknowledged_time == 0:
            return False
        return self.acknowledged_time <= int(datetime.datetime.now().timestamp())


@dataclass
class Subscription:
    """Data model for a subscription"""
    name: str
    gug_name: str
    queries: List[Query]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """Create Subscription instance from dictionary"""
        queries = [Query.from_dict(q) for q in data.get('queries', [])]
        return cls(
            name=data.get('name', 'Unknown'),
            gug_name=data.get('gug_name', ''),
            queries=queries
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Subscription instance to dictionary"""
        return {
            'name': self.name,
            'gug_name': self.gug_name,
            'queries': [q.to_dict() for q in self.queries]
        }
    
    @property
    def query_count(self) -> int:
        """Get number of queries in this subscription"""
        return len(self.queries)
    
    @property
    def active_query_count(self) -> int:
        """Get number of non-acknowledged queries"""
        return len([q for q in self.queries if not q.acknowledged])
    
    @property
    def acknowledged_query_count(self) -> int:
        """Get number of acknowledged queries"""
        return len([q for q in self.queries if q.acknowledged])


@dataclass
class SubscriptionData:
    """Container for all subscription data"""
    subscriptions: List[Subscription]
    version: int
    hydrus_version: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionData':
        """Create SubscriptionData instance from dictionary"""
        subscriptions = [Subscription.from_dict(s) for s in data.get('subscriptions', [])]
        return cls(
            subscriptions=subscriptions,
            version=data.get('version', 80),
            hydrus_version=data.get('hydrus_version', 'Unknown')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SubscriptionData instance to dictionary"""
        return {
            'subscriptions': [s.to_dict() for s in self.subscriptions],
            'version': self.version,
            'hydrus_version': self.hydrus_version
        }
    
    @property
    def total_queries(self) -> int:
        """Get total number of queries across all subscriptions"""
        return sum(s.query_count for s in self.subscriptions)
    
    @property
    def total_active_queries(self) -> int:
        """Get total number of active (non-acknowledged) queries"""
        return sum(s.active_query_count for s in self.subscriptions)
    
    def get_subscription_by_name(self, name: str) -> Optional[Subscription]:
        """Get subscription by name"""
        for sub in self.subscriptions:
            if sub.name == name:
                return sub
        return None
    
    def get_all_queries(self) -> List[tuple[str, Query]]:
        """Get all queries with their subscription names"""
        all_queries = []
        for sub in self.subscriptions:
            for query in sub.queries:
                all_queries.append((sub.name, query))
        return all_queries