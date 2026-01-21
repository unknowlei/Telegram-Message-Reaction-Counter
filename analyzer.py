"""
数据分析和排序模块

负责对获取的消息数据进行分析、排序和统计
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

import config


class MessageAnalyzer:
    """消息分析器"""
    
    def __init__(self, messages: List[Dict[str, Any]]):
        """
        初始化分析器
        
        Args:
            messages: 消息数据列表
        """
        self.messages = messages
        self.sorted_messages: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}
    
    def sort_by_reactions(self, reverse: bool = True) -> List[Dict[str, Any]]:
        """
        按反应数量排序
        
        Args:
            reverse: 是否降序排列
            
        Returns:
            list: 排序后的消息列表
        """
        self.sorted_messages = sorted(
            self.messages,
            key=lambda x: x['total_reactions'],
            reverse=reverse
        )
        
        return self.sorted_messages
    
    def sort_by_views(self, reverse: bool = True) -> List[Dict[str, Any]]:
        """
        按浏览量排序
        
        Args:
            reverse: 是否降序排列
            
        Returns:
            list: 排序后的消息列表
        """
        # 过滤掉没有浏览量的消息
        messages_with_views = [m for m in self.messages if m.get('views')]
        
        self.sorted_messages = sorted(
            messages_with_views,
            key=lambda x: x['views'] or 0,
            reverse=reverse
        )
        
        return self.sorted_messages
    
    def sort_by_engagement_rate(self, reverse: bool = True) -> List[Dict[str, Any]]:
        """
        按互动率排序（反应数/浏览量）
        
        Args:
            reverse: 是否降序排列
            
        Returns:
            list: 排序后的消息列表
        """
        # 过滤掉没有浏览量的消息
        messages_with_views = [m for m in self.messages if m.get('views') and m['views'] > 0]
        
        # 计算互动率
        for msg in messages_with_views:
            msg['engagement_rate'] = (msg['total_reactions'] / msg['views']) * 100
        
        self.sorted_messages = sorted(
            messages_with_views,
            key=lambda x: x.get('engagement_rate', 0),
            reverse=reverse
        )
        
        return self.sorted_messages
    
    def sort_by_replies(self, reverse: bool = True) -> List[Dict[str, Any]]:
        """
        按回复数排序
        
        Args:
            reverse: 是否降序排列
            
        Returns:
            list: 排序后的消息列表
        """
        self.sorted_messages = sorted(
            self.messages,
            key=lambda x: x.get('replies', 0) or 0,
            reverse=reverse
        )
        
        return self.sorted_messages
    
    def filter_by_media_type(
        self,
        media_types: List[str],
        messages: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按媒体类型过滤
        
        Args:
            media_types: 媒体类型列表，如 ['archive', 'executable', 'video']
            messages: 要过滤的消息列表，默认使用 self.messages
            
        Returns:
            list: 过滤后的消息列表
        """
        source = messages or self.messages
        
        return [
            m for m in source
            if m['media']['has_media'] and m['media']['type'] in media_types
        ]
    
    def filter_by_date_range(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        days: int = None,
        messages: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按日期范围过滤
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            days: 最近 N 天（与 start_date/end_date 互斥）
            messages: 要过滤的消息列表
            
        Returns:
            list: 过滤后的消息列表
        """
        source = messages or self.messages
        
        if days:
            end_date = datetime.now(source[0]['date'].tzinfo) if source else datetime.now()
            start_date = end_date - timedelta(days=days)
        
        filtered = []
        for msg in source:
            msg_date = msg['date']
            if start_date and msg_date < start_date:
                continue
            if end_date and msg_date > end_date:
                continue
            filtered.append(msg)
        
        return filtered
    
    def filter_by_keyword(
        self,
        keywords: List[str],
        case_sensitive: bool = False,
        messages: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按关键词过滤
        
        Args:
            keywords: 关键词列表
            case_sensitive: 是否区分大小写
            messages: 要过滤的消息列表
            
        Returns:
            list: 过滤后的消息列表
        """
        source = messages or self.messages
        
        if not case_sensitive:
            keywords = [k.lower() for k in keywords]
        
        filtered = []
        for msg in source:
            text = msg['text'] or ''
            filename = msg['media'].get('filename') or ''
            
            if not case_sensitive:
                text = text.lower()
                filename = filename.lower()
            
            search_text = f"{text} {filename}"
            
            if any(k in search_text for k in keywords):
                filtered.append(msg)
        
        return filtered
    
    def get_reaction_statistics(self) -> Dict[str, Any]:
        """
        获取反应统计数据
        
        Returns:
            dict: 统计数据
        """
        emoji_counts = defaultdict(int)
        emoji_messages = defaultdict(int)  # 使用该表情的消息数
        
        for msg in self.messages:
            for r in msg['reactions']:
                emoji = r['emoji']
                emoji_counts[emoji] += r['count']
                emoji_messages[emoji] += 1
        
        # 排序表情
        sorted_emojis = sorted(
            emoji_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'emoji_counts': dict(sorted_emojis),
            'emoji_messages': dict(emoji_messages),
            'top_emojis': sorted_emojis[:10],
            'total_reactions': sum(emoji_counts.values()),
            'unique_emojis': len(emoji_counts),
        }
    
    def get_media_statistics(self) -> Dict[str, Any]:
        """
        获取媒体类型统计
        
        Returns:
            dict: 统计数据
        """
        type_counts = defaultdict(int)
        type_reactions = defaultdict(int)
        
        for msg in self.messages:
            media = msg['media']
            if media['has_media']:
                mtype = media['type'] or 'unknown'
                type_counts[mtype] += 1
                type_reactions[mtype] += msg['total_reactions']
        
        # 计算每种类型的平均反应数
        type_avg = {}
        for mtype, count in type_counts.items():
            type_avg[mtype] = type_reactions[mtype] / count if count > 0 else 0
        
        return {
            'type_counts': dict(type_counts),
            'type_reactions': dict(type_reactions),
            'type_average': type_avg,
        }
    
    def get_time_statistics(self) -> Dict[str, Any]:
        """
        获取时间统计
        
        Returns:
            dict: 统计数据
        """
        if not self.messages:
            return {}
        
        # 按小时统计
        hour_counts = defaultdict(int)
        hour_reactions = defaultdict(int)
        
        # 按星期统计
        weekday_counts = defaultdict(int)
        weekday_reactions = defaultdict(int)
        
        for msg in self.messages:
            date = msg['date']
            hour = date.hour
            weekday = date.weekday()
            
            hour_counts[hour] += 1
            hour_reactions[hour] += msg['total_reactions']
            
            weekday_counts[weekday] += 1
            weekday_reactions[weekday] += msg['total_reactions']
        
        # 找出最佳发布时间
        best_hour = max(hour_reactions.items(), key=lambda x: x[1])[0] if hour_reactions else None
        best_weekday = max(weekday_reactions.items(), key=lambda x: x[1])[0] if weekday_reactions else None
        
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        return {
            'hour_distribution': dict(hour_counts),
            'hour_reactions': dict(hour_reactions),
            'weekday_distribution': dict(weekday_counts),
            'weekday_reactions': dict(weekday_reactions),
            'best_hour': best_hour,
            'best_weekday': weekday_names[best_weekday] if best_weekday is not None else None,
        }
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        生成综合统计摘要
        
        Returns:
            dict: 摘要数据
        """
        if not self.messages:
            return {'message': '没有消息数据'}
        
        total_reactions = sum(m['total_reactions'] for m in self.messages)
        total_views = sum(m['views'] or 0 for m in self.messages)
        
        # 找到最热门的消息
        sorted_by_reactions = sorted(
            self.messages,
            key=lambda x: x['total_reactions'],
            reverse=True
        )
        
        top_message = sorted_by_reactions[0] if sorted_by_reactions else None
        
        # 日期范围
        dates = [m['date'] for m in self.messages]
        
        self.statistics = {
            'total_messages': len(self.messages),
            'total_reactions': total_reactions,
            'total_views': total_views,
            'avg_reactions': total_reactions / len(self.messages) if self.messages else 0,
            'avg_views': total_views / len(self.messages) if self.messages else 0,
            'date_range': {
                'start': min(dates) if dates else None,
                'end': max(dates) if dates else None,
            },
            'top_message': {
                'id': top_message['id'],
                'reactions': top_message['total_reactions'],
                'link': top_message['link'],
            } if top_message else None,
            'reaction_stats': self.get_reaction_statistics(),
            'media_stats': self.get_media_statistics(),
            'time_stats': self.get_time_statistics(),
        }
        
        return self.statistics
    
    def get_top_n(
        self,
        n: int = None,
        sort_by: str = 'reactions'
    ) -> List[Dict[str, Any]]:
        """
        获取 Top N 消息
        
        Args:
            n: 数量，默认使用配置值
            sort_by: 排序依据，可选 'reactions', 'views', 'engagement'
            
        Returns:
            list: Top N 消息列表
        """
        n = n or config.TOP_N_DISPLAY
        
        if sort_by == 'views':
            self.sort_by_views()
        elif sort_by == 'engagement':
            self.sort_by_engagement_rate()
        else:
            self.sort_by_reactions()
        
        return self.sorted_messages[:n]


def print_top_messages(
    messages: List[Dict[str, Any]],
    n: int = 20,
    show_reactions: bool = True
):
    """
    打印 Top 消息
    
    Args:
        messages: 消息列表
        n: 显示数量
        show_reactions: 是否显示详细反应
    """
    print(f"\n{'='*60}")
    print(f"  Top {n} 最热门消息")
    print(f"{'='*60}\n")
    
    for i, msg in enumerate(messages[:n], 1):
        # 标题行
        reactions_str = f"🔥 {msg['total_reactions']} 反应"
        views_str = f"👁 {msg['views']} 浏览" if msg.get('views') else ""
        
        print(f"#{i} | {reactions_str} | {views_str}")
        
        # 内容预览
        text = msg['text'] or ''
        if text:
            preview = (text[:60] + '...') if len(text) > 60 else text
            preview = preview.replace('\n', ' ')
            print(f"   📝 {preview}")
        
        # 媒体信息
        media = msg['media']
        if media['has_media']:
            media_str = f"   📎 [{media['type']}]"
            if media['filename']:
                media_str += f" {media['filename']}"
            if media['size']:
                size_mb = media['size'] / (1024 * 1024)
                media_str += f" ({size_mb:.1f} MB)"
            print(media_str)
        
        # 反应详情
        if show_reactions and msg['reactions']:
            reactions_detail = ' '.join(
                f"{r['emoji']}×{r['count']}" for r in msg['reactions']
            )
            print(f"   💬 {reactions_detail}")
        
        # 链接
        print(f"   🔗 {msg['link']}")
        print()


def print_statistics(stats: Dict[str, Any]):
    """
    打印统计信息
    
    Args:
        stats: 统计数据
    """
    print(f"\n{'='*60}")
    print(f"  统计摘要")
    print(f"{'='*60}\n")
    
    print(f"📊 总体数据:")
    print(f"   消息数量: {stats['total_messages']}")
    print(f"   总反应数: {stats['total_reactions']}")
    print(f"   总浏览量: {stats['total_views']}")
    print(f"   平均反应: {stats['avg_reactions']:.1f}")
    print(f"   平均浏览: {stats['avg_views']:.1f}")
    
    if stats.get('date_range', {}).get('start'):
        start = stats['date_range']['start'].strftime('%Y-%m-%d')
        end = stats['date_range']['end'].strftime('%Y-%m-%d')
        print(f"   日期范围: {start} ~ {end}")
    
    # 表情统计
    reaction_stats = stats.get('reaction_stats', {})
    if reaction_stats.get('top_emojis'):
        print(f"\n🎭 热门表情:")
        for emoji, count in reaction_stats['top_emojis'][:5]:
            print(f"   {emoji}: {count} 次")
    
    # 媒体统计
    media_stats = stats.get('media_stats', {})
    if media_stats.get('type_counts'):
        print(f"\n📁 媒体类型:")
        for mtype, count in media_stats['type_counts'].items():
            avg = media_stats['type_average'].get(mtype, 0)
            print(f"   {mtype}: {count} 个 (平均 {avg:.1f} 反应)")
    
    # 时间统计
    time_stats = stats.get('time_stats', {})
    if time_stats.get('best_hour') is not None:
        print(f"\n⏰ 最佳发布时间:")
        print(f"   时段: {time_stats['best_hour']}:00")
        if time_stats.get('best_weekday'):
            print(f"   星期: {time_stats['best_weekday']}")
    
    print()