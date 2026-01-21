"""
消息和反应获取模块

负责从 Telegram 频道/群组获取消息和反应数据
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    ChannelInvalidError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import (
    Channel,
    Chat,
    User,
    MessageMediaDocument,
    MessageMediaPhoto,
    MessageMediaWebPage,
    ReactionEmoji,
    ReactionCustomEmoji,
    DocumentAttributeFilename,
)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

import config


class TelegramFetcher:
    """Telegram 消息获取器"""
    
    def __init__(self):
        """初始化获取器"""
        self.client: Optional[TelegramClient] = None
        self.channel = None
        self.channel_info: Dict[str, Any] = {}
        
    async def connect(self) -> bool:
        """
        连接到 Telegram
        
        Returns:
            bool: 连接成功返回 True
        """
        print("正在连接到 Telegram...")
        
        self.client = TelegramClient(
            config.SESSION_NAME,
            config.API_ID,
            config.API_HASH
        )
        
        await self.client.start()
        
        # 获取当前用户信息
        me = await self.client.get_me()
        print(f"✓ 已登录: {me.first_name} (@{me.username or 'N/A'})")
        
        return True
    
    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.disconnect()
            print("已断开 Telegram 连接")
    
    async def get_channel(self, channel_identifier: Union[str, int] = None) -> bool:
        """
        获取目标频道/群组
        
        Args:
            channel_identifier: 频道标识（用户名、链接或ID），默认使用配置文件中的值
            
        Returns:
            bool: 获取成功返回 True
        """
        target = channel_identifier or config.TARGET_CHANNEL
        
        print(f"正在获取频道信息: {target}")
        
        try:
            self.channel = await self.client.get_entity(target)
            
            # 提取频道信息
            if isinstance(self.channel, Channel):
                self.channel_info = {
                    'id': self.channel.id,
                    'title': self.channel.title,
                    'username': self.channel.username,
                    'is_channel': self.channel.broadcast,  # True=频道, False=超级群组
                    'participants_count': getattr(self.channel, 'participants_count', None),
                }
            elif isinstance(self.channel, Chat):
                self.channel_info = {
                    'id': self.channel.id,
                    'title': self.channel.title,
                    'username': None,
                    'is_channel': False,
                    'participants_count': getattr(self.channel, 'participants_count', None),
                }
            else:
                print(f"⚠ 警告: 目标不是频道或群组，而是 {type(self.channel).__name__}")
                self.channel_info = {
                    'id': getattr(self.channel, 'id', None),
                    'title': getattr(self.channel, 'title', str(target)),
                    'username': getattr(self.channel, 'username', None),
                    'is_channel': False,
                    'participants_count': None,
                }
            
            print(f"✓ 已获取: {self.channel_info['title']}")
            if self.channel_info['username']:
                print(f"  用户名: @{self.channel_info['username']}")
            print(f"  ID: {self.channel_info['id']}")
            print(f"  类型: {'频道' if self.channel_info['is_channel'] else '群组'}")
            
            return True
            
        except ChannelPrivateError:
            print("✗ 错误: 这是一个私有频道，你没有访问权限")
            return False
        except ChannelInvalidError:
            print("✗ 错误: 无效的频道")
            return False
        except UsernameInvalidError:
            print("✗ 错误: 无效的用户名格式")
            return False
        except UsernameNotOccupiedError:
            print("✗ 错误: 该用户名不存在")
            return False
        except Exception as e:
            print(f"✗ 错误: {type(e).__name__}: {e}")
            return False
    
    def _get_reaction_info(self, reaction) -> Dict[str, Any]:
        """
        解析反应信息
        
        Args:
            reaction: 反应对象
            
        Returns:
            dict: 包含表情和数量的字典
        """
        if isinstance(reaction.reaction, ReactionEmoji):
            emoji = reaction.reaction.emoticon
            emoji_type = "standard"
        elif isinstance(reaction.reaction, ReactionCustomEmoji):
            emoji = f"[自定义:{reaction.reaction.document_id}]"
            emoji_type = "custom"
        else:
            emoji = "❓"
            emoji_type = "unknown"
        
        return {
            'emoji': emoji,
            'type': emoji_type,
            'count': reaction.count,
        }
    
    def _get_media_info(self, message) -> Dict[str, Any]:
        """
        获取消息媒体信息
        
        Args:
            message: 消息对象
            
        Returns:
            dict: 媒体信息
        """
        if not message.media:
            return {'has_media': False, 'type': None, 'filename': None, 'size': None}
        
        media = message.media
        info = {'has_media': True, 'type': None, 'filename': None, 'size': None}
        
        if isinstance(media, MessageMediaDocument):
            info['type'] = 'document'
            doc = media.document
            if doc:
                info['size'] = doc.size
                # 尝试获取文件名
                for attr in doc.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        info['filename'] = attr.file_name
                        # 根据扩展名细分类型
                        name = attr.file_name.lower()
                        if name.endswith(('.zip', '.rar', '.7z', '.tar', '.gz')):
                            info['type'] = 'archive'
                        elif name.endswith(('.exe', '.msi', '.apk', '.ipa')):
                            info['type'] = 'executable'
                        elif name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')):
                            info['type'] = 'video'
                        elif name.endswith(('.mp3', '.flac', '.wav', '.aac', '.ogg')):
                            info['type'] = 'audio'
                        elif name.endswith(('.pdf', '.doc', '.docx', '.txt', '.epub')):
                            info['type'] = 'document'
                        elif name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                            info['type'] = 'image'
                        break
        elif isinstance(media, MessageMediaPhoto):
            info['type'] = 'photo'
        elif isinstance(media, MessageMediaWebPage):
            info['type'] = 'webpage'
        else:
            info['type'] = type(media).__name__
        
        return info
    
    def _get_message_link(self, message_id: int) -> dict:
        """
        生成消息链接（包含深度链接和普通链接）
        
        Args:
            message_id: 消息 ID
            
        Returns:
            dict: 包含 tg_link（深度链接）和 web_link（网页链接）的字典
        """
        if self.channel_info.get('username'):
            username = self.channel_info['username']
            return {
                'tg_link': f"tg://resolve?domain={username}&post={message_id}",
                'web_link': f"https://t.me/{username}/{message_id}"
            }
        else:
            # 私有频道/群组需要特殊格式
            channel_id = str(self.channel_info['id'])
            # 去掉 -100 前缀（如果有的话）
            if channel_id.startswith('-100'):
                short_id = channel_id[4:]
            elif channel_id.startswith('-'):
                short_id = channel_id[1:]
            else:
                short_id = channel_id
            return {
                'tg_link': f"tg://privatepost?channel={short_id}&post={message_id}",
                'web_link': f"https://t.me/c/{short_id}/{message_id}"
            }
    
    async def fetch_messages(
        self,
        limit: int = None,
        min_reactions: int = None,
        media_only: bool = None,
        progress_callback=None,
        offset_date: datetime = None,
        end_date: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        获取消息和反应数据
        
        Args:
            limit: 最大消息数量
            min_reactions: 最小反应数阈值
            media_only: 是否只获取包含媒体的消息
            progress_callback: 进度回调函数
            offset_date: 开始日期（获取此日期之后的消息）
            end_date: 结束日期（获取此日期之前的消息，用于 iter_messages 的 offset_date）
            
        Returns:
            list: 消息数据列表
        """
        # 如果 limit 为 None，则不限制消息数量
        if limit is None:
            limit = float('inf')  # 无限制
        elif limit == 0:
            limit = config.MAX_MESSAGES
        min_reactions = min_reactions if min_reactions is not None else config.MIN_REACTIONS
        media_only = media_only if media_only is not None else config.MEDIA_ONLY
        
        print(f"\n开始获取消息...")
        print(f"  最大数量: {limit}")
        print(f"  最小反应数: {min_reactions}")
        print(f"  仅媒体消息: {'是' if media_only else '否'}")
        if offset_date:
            print(f"  开始日期: {offset_date}")
        if end_date:
            print(f"  结束日期: {end_date}")
        print()
        
        messages_data = []
        processed = 0
        skipped_no_reactions = 0
        skipped_no_media = 0
        skipped_out_of_range = 0
        
        # 创建进度条（如果可用）
        pbar = None
        if HAS_TQDM:
            pbar = tqdm(total=limit, desc="获取消息", unit="条")
        
        try:
            # 使用 offset_date 参数让 Telegram API 从指定日期开始返回消息
            # Telegram 的 iter_messages 是倒序的（最新的消息先返回）
            # offset_date 是获取此日期之前的消息
            # 如果是无限制，则不传入 limit 参数
            iter_limit = None if limit == float('inf') else limit
            async for message in self.client.iter_messages(self.channel, limit=iter_limit, offset_date=end_date):
                processed += 1
                
                # 更新进度条
                if pbar:
                    pbar.update(1)
                elif processed % 100 == 0:
                    print(f"  已处理: {processed} 条消息...")
                
                # 检查日期范围 - 如果消息日期早于开始日期，提前终止
                if offset_date and message.date < offset_date:
                    skipped_out_of_range += 1
                    # 由于消息是按时间倒序的，一旦遇到早于开始日期的消息，后面的都会更早
                    # 但为了保险起见，我们累计跳过一定数量后终止
                    if skipped_out_of_range >= 10:
                        print(f"\n已到达开始日期边界，提前终止获取")
                        break
                    continue
                
                # 跳过没有反应的消息
                if not message.reactions:
                    skipped_no_reactions += 1
                    continue
                
                # 获取媒体信息
                media_info = self._get_media_info(message)
                
                # 如果只要媒体消息，跳过没有媒体的
                if media_only and not media_info['has_media']:
                    skipped_no_media += 1
                    continue
                
                # 解析反应
                reactions = []
                total_reactions = 0
                for r in message.reactions.results:
                    reaction_info = self._get_reaction_info(r)
                    reactions.append(reaction_info)
                    total_reactions += reaction_info['count']
                
                # 过滤低于阈值的消息
                if total_reactions < min_reactions:
                    skipped_no_reactions += 1
                    continue
                
                # 构建消息数据
                msg_data = {
                    'id': message.id,
                    'date': message.date,
                    'text': message.text or '',
                    'media': media_info,
                    'reactions': reactions,
                    'total_reactions': total_reactions,
                    'views': message.views,
                    'forwards': message.forwards,
                    'replies': message.replies.replies if message.replies else 0,
                    'link': self._get_message_link(message.id),
                }
                
                messages_data.append(msg_data)
                
                # 回调
                if progress_callback:
                    progress_callback(processed, len(messages_data))
                
                # 批次延迟
                if processed % config.BATCH_SIZE == 0:
                    await asyncio.sleep(config.BATCH_DELAY)
                    
        except FloodWaitError as e:
            print(f"\n⚠ 触发速率限制，需要等待 {e.seconds} 秒...")
            if pbar:
                pbar.close()
            await asyncio.sleep(e.seconds)
            # 这里可以选择重试或返回已获取的数据
            print("继续处理已获取的数据...")
        
        finally:
            if pbar:
                pbar.close()
        
        print(f"\n获取完成!")
        print(f"  总处理: {processed} 条消息")
        print(f"  有效消息: {len(messages_data)} 条")
        print(f"  跳过（反应不足）: {skipped_no_reactions} 条")
        if media_only:
            print(f"  跳过（无媒体）: {skipped_no_media} 条")
        if offset_date:
            print(f"  跳过（超出日期范围）: {skipped_out_of_range} 条")
        
        return messages_data
    
    async def list_dialogs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出用户加入的对话（频道/群组）
        
        Args:
            limit: 最大数量
            
        Returns:
            list: 对话列表
        """
        dialogs = []
        
        async for dialog in self.client.iter_dialogs(limit=limit):
            if isinstance(dialog.entity, (Channel, Chat)):
                dialogs.append({
                    'id': dialog.id,
                    'name': dialog.name,
                    'username': getattr(dialog.entity, 'username', None),
                    'is_channel': isinstance(dialog.entity, Channel) and dialog.entity.broadcast,
                    'unread_count': dialog.unread_count,
                })
        
        return dialogs


async def main():
    """测试函数"""
    fetcher = TelegramFetcher()
    
    try:
        # 连接
        await fetcher.connect()
        
        # 列出对话
        print("\n你加入的频道/群组:")
        print("-" * 50)
        dialogs = await fetcher.list_dialogs(20)
        for i, d in enumerate(dialogs, 1):
            prefix = "📢" if d['is_channel'] else "👥"
            username = f" (@{d['username']})" if d['username'] else ""
            print(f"{i}. {prefix} {d['name']}{username}")
        
        # 如果配置了目标频道，尝试获取
        if config.TARGET_CHANNEL and config.TARGET_CHANNEL != "your_channel_username":
            print("\n" + "=" * 50)
            if await fetcher.get_channel():
                messages = await fetcher.fetch_messages(limit=100)
                print(f"\n获取到 {len(messages)} 条有效消息")
                
                if messages:
                    print("\nTop 5 消息预览:")
                    sorted_msgs = sorted(messages, key=lambda x: x['total_reactions'], reverse=True)
                    for msg in sorted_msgs[:5]:
                        text_preview = (msg['text'][:50] + '...') if len(msg['text']) > 50 else msg['text'] or '[媒体]'
                        print(f"  [{msg['total_reactions']}反应] {text_preview}")
        
    finally:
        await fetcher.disconnect()


if __name__ == "__main__":
    asyncio.run(main())