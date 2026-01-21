#!/usr/bin/env python3
"""
Telegram Reaction Counter - Web 可视化界面
"""

import asyncio
import os
import sys
import threading
import time
import traceback

from flask import Flask, render_template, request, jsonify, send_file

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
)

import config
from fetcher import TelegramFetcher
from analyzer import MessageAnalyzer
from exporter import Exporter

app = Flask(__name__)
app.secret_key = os.urandom(24)


class TelegramManager:
    """管理 Telegram 连接"""
    
    def __init__(self):
        self.loop = None
        self.thread = None
        self.client = None
        self.fetcher = None
        
        self.phone = None
        self.phone_code_hash = None
        self.is_logged_in = False
        self.user_info = None
        self.last_error = None
        
        self.task_progress = {
            'status': 'idle',
            'progress': 0,
            'message': '',
            'data': None
        }
        
        self._start_event_loop()
    
    def _start_event_loop(self):
        """在后台线程启动事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        # 等待循环启动
        while self.loop is None or not self.loop.is_running():
            time.sleep(0.05)
    
    def run_async(self, coro, timeout=120):
        """在事件循环中运行协程并等待结果"""
        if self.loop is None or not self.loop.is_running():
            self._start_event_loop()
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            self.last_error = str(e)
            raise
    
    def get_session_name(self, phone):
        """根据手机号生成 session 文件名"""
        clean_phone = ''.join(filter(str.isdigit, phone))
        return f"session_{clean_phone}"
    
    def reset(self):
        """重置状态"""
        async def _disconnect():
            if self.client and self.client.is_connected():
                await self.client.disconnect()
        
        try:
            if self.client:
                self.run_async(_disconnect(), timeout=10)
        except:
            pass
        
        self.client = None
        self.fetcher = None
        self.phone = None
        self.phone_code_hash = None
        self.is_logged_in = False
        self.user_info = None
        self.task_progress = {
            'status': 'idle',
            'progress': 0,
            'message': '',
            'data': None
        }
    
    async def _send_code_async(self, phone):
        """发送验证码 - 异步版本"""
        print(f"[DEBUG] 开始发送验证码到: {phone}")
        
        # 格式化手机号
        if not phone.startswith('+'):
            phone = '+' + phone
        
        self.phone = phone
        session_name = self.get_session_name(phone)
        print(f"[DEBUG] Session 名称: {session_name}")
        
        # 如果已有客户端，先断开
        if self.client:
            print("[DEBUG] 断开现有客户端...")
            try:
                if self.client.is_connected():
                    await self.client.disconnect()
            except Exception as e:
                print(f"[DEBUG] 断开时出错: {e}")
            self.client = None
        
        # 检查 API 凭证
        print(f"[DEBUG] API_ID: {config.API_ID}, API_HASH: {config.API_HASH[:8]}...")
        
        # 创建新客户端
        print("[DEBUG] 创建新客户端...")
        self.client = TelegramClient(
            session_name,
            config.API_ID,
            config.API_HASH
        )
        
        # 连接
        print("[DEBUG] 正在连接到 Telegram...")
        await self.client.connect()
        print(f"[DEBUG] 连接成功: {self.client.is_connected()}")
        
        # 检查是否已登录
        if await self.client.is_user_authorized():
            print("[DEBUG] 已经登录，获取用户信息...")
            me = await self.client.get_me()
            self.is_logged_in = True
            self.user_info = {
                'name': me.first_name or '',
                'username': me.username or '',
                'phone': me.phone or ''
            }
            
            # 创建 fetcher
            self.fetcher = TelegramFetcher()
            self.fetcher.client = self.client
            
            print(f"[DEBUG] 已登录用户: {self.user_info}")
            return {'success': True, 'already_logged_in': True, 'user': self.user_info}
        
        # 发送验证码
        print("[DEBUG] 发送验证码请求...")
        sent = await self.client.send_code_request(phone)
        self.phone_code_hash = sent.phone_code_hash
        print(f"[DEBUG] 验证码已发送，phone_code_hash: {self.phone_code_hash[:10]}...")
        
        return {'success': True, 'already_logged_in': False, 'message': '验证码已发送到 Telegram'}
    
    def send_code(self, phone):
        """发送验证码 - 同步包装"""
        try:
            print(f"[DEBUG] send_code 开始: {phone}")
            result = self.run_async(self._send_code_async(phone))
            print(f"[DEBUG] send_code 结果: {result}")
            return result
        except PhoneNumberInvalidError:
            print("[DEBUG] 手机号格式无效")
            self.reset()
            return {'success': False, 'error': '手机号格式无效，请使用国际格式如 +8613800138000'}
        except FloodWaitError as e:
            print(f"[DEBUG] FloodWait: {e.seconds}秒")
            self.reset()
            return {'success': False, 'error': f'请求过于频繁，请等待 {e.seconds} 秒后重试'}
        except Exception as e:
            error_msg = str(e)
            print(f"[DEBUG] 发送验证码异常: {error_msg}")
            print(f"[DEBUG] 详细错误:\n{traceback.format_exc()}")
            self.reset()
            return {'success': False, 'error': f'发送验证码失败: {error_msg}'}
    
    async def _verify_code_async(self, code):
        """验证码登录 - 异步版本"""
        if not self.client or not self.client.is_connected():
            raise Exception("客户端未连接，请重新发送验证码")
        
        await self.client.sign_in(
            self.phone,
            code,
            phone_code_hash=self.phone_code_hash
        )
        
        me = await self.client.get_me()
        self.is_logged_in = True
        self.phone_code_hash = None
        self.user_info = {
            'name': me.first_name or '',
            'username': me.username or '',
            'phone': me.phone or ''
        }
        
        # 创建 fetcher
        self.fetcher = TelegramFetcher()
        self.fetcher.client = self.client
        
        return {'success': True, 'user': self.user_info}
    
    def verify_code(self, code):
        """验证码登录 - 同步包装"""
        try:
            return self.run_async(self._verify_code_async(code))
        except SessionPasswordNeededError:
            return {'success': False, 'error': '该账号启用了两步验证，请输入密码', 'need_password': True}
        except PhoneCodeInvalidError:
            return {'success': False, 'error': '验证码错误，请检查后重新输入'}
        except PhoneCodeExpiredError:
            self.phone_code_hash = None
            return {'success': False, 'error': '验证码已过期，请重新发送'}
        except Exception as e:
            return {'success': False, 'error': f'登录失败: {str(e)}'}
    
    async def _verify_password_async(self, password):
        """两步验证密码 - 异步版本"""
        await self.client.sign_in(password=password)
        
        me = await self.client.get_me()
        self.is_logged_in = True
        self.phone_code_hash = None
        self.user_info = {
            'name': me.first_name or '',
            'username': me.username or '',
            'phone': me.phone or ''
        }
        
        # 创建 fetcher
        self.fetcher = TelegramFetcher()
        self.fetcher.client = self.client
        
        return {'success': True, 'user': self.user_info}
    
    def verify_password(self, password):
        """两步验证密码 - 同步包装"""
        try:
            return self.run_async(self._verify_password_async(password))
        except Exception as e:
            return {'success': False, 'error': f'密码验证失败: {str(e)}'}
    
    async def _logout_async(self, delete_session):
        """登出 - 异步版本"""
        session_file = None
        if self.phone:
            session_file = self.get_session_name(self.phone) + '.session'
        
        # 断开连接
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        
        # 重置
        self.client = None
        self.fetcher = None
        self.phone = None
        self.phone_code_hash = None
        self.is_logged_in = False
        self.user_info = None
        
        # 如果需要删除 session 文件
        if delete_session and session_file and os.path.exists(session_file):
            os.remove(session_file)
            return {'success': True, 'message': '已登出并删除登录状态'}
        
        return {'success': True, 'message': '已登出'}
    
    def logout(self, delete_session=False):
        """登出 - 同步包装"""
        try:
            return self.run_async(self._logout_async(delete_session), timeout=10)
        except:
            # 强制重置
            self.client = None
            self.fetcher = None
            self.phone = None
            self.phone_code_hash = None
            self.is_logged_in = False
            self.user_info = None
            return {'success': True, 'message': '已登出'}
    
    async def _get_dialogs_async(self):
        """获取对话列表 - 异步版本"""
        if not self.fetcher:
            raise Exception("未登录")
        dialogs = await self.fetcher.list_dialogs(50)
        return {'success': True, 'dialogs': dialogs}
    
    def get_dialogs(self):
        """获取对话列表 - 同步包装"""
        try:
            return self.run_async(self._get_dialogs_async())
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _analyze_async(self, channel, days, min_reactions, media_only, sort_by, emojis, date_from=None, date_to=None):
        """分析频道 - 异步版本"""
        from datetime import datetime, timedelta, timezone
        
        try:
            self.task_progress['message'] = '正在获取频道信息...'
            self.task_progress['progress'] = 10
            
            # 尝试获取频道
            success = await self.fetcher.get_channel(channel)
            if not success:
                self.task_progress = {'status': 'error', 'progress': 0, 'message': '无法获取频道，请检查频道名称或确认已加入', 'data': None}
                return
            
            self.task_progress['message'] = '正在获取消息...'
            self.task_progress['progress'] = 20
            
            # 计算时间范围
            start_date = None
            end_date = None
            
            if days == -1 and date_from:
                # 自定义日期范围
                try:
                    start_date = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                    if date_to:
                        end_date = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
                except:
                    pass
            elif days > 0:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                end_date = datetime.now(timezone.utc)
            # days == 0 表示全部消息，不设置日期限制
            
            # 获取消息 - 使用日期参数让 API 直接返回时间范围内的消息
            limit = 10000  # 最多获取1万条
            
            def progress_callback(processed, valid):
                self.task_progress['message'] = f'已处理 {processed} 条消息，有效 {valid} 条'
                self.task_progress['progress'] = 20 + min(int((processed / 1000) * 60), 60)
            
            messages = await self.fetcher.fetch_messages(
                limit=limit,
                min_reactions=min_reactions,
                media_only=media_only,
                progress_callback=progress_callback,
                offset_date=start_date,
                end_date=end_date
            )
            
            if not messages:
                self.task_progress = {'status': 'error', 'progress': 0, 'message': '没有找到符合条件的消息', 'data': None}
                return
            
            self.task_progress['message'] = '正在分析数据...'
            self.task_progress['progress'] = 85
            
            analyzer = MessageAnalyzer(messages)
            
            # 排序逻辑：如果选择了表情，优先按表情数量排序
            if emojis and len(emojis) > 0:
                # 有选中的表情，按选中表情数量排序
                sorted_messages = self._sort_by_emojis(messages, emojis)
            elif sort_by == 'views':
                sorted_messages = analyzer.sort_by_views()
            elif sort_by == 'engagement':
                sorted_messages = analyzer.sort_by_engagement_rate()
            else:
                sorted_messages = analyzer.sort_by_reactions()
            
            stats = analyzer.generate_summary()
            
            self.task_progress['message'] = '正在准备结果...'
            self.task_progress['progress'] = 95
            
            # 处理日期序列化
            for msg in sorted_messages:
                if msg.get('date'):
                    msg['date'] = msg['date'].isoformat()
            
            if stats.get('date_range'):
                if stats['date_range'].get('start'):
                    stats['date_range']['start'] = stats['date_range']['start'].isoformat()
                if stats['date_range'].get('end'):
                    stats['date_range']['end'] = stats['date_range']['end'].isoformat()
            
            self.task_progress = {
                'status': 'completed',
                'progress': 100,
                'message': '分析完成',
                'data': {
                    'messages': sorted_messages[:100],
                    'all_messages': sorted_messages,
                    'stats': stats,
                    'channel_info': self.fetcher.channel_info,
                    'total_count': len(sorted_messages)
                }
            }
            
        except Exception as e:
            self.task_progress = {
                'status': 'error',
                'progress': 0,
                'message': f'错误: {str(e)}',
                'data': None
            }
    
    def _sort_by_emojis(self, messages, emojis):
        """按指定表情的总反应数量排序"""
        import unicodedata
        
        # 规范化 emoji，移除变体选择符等
        def normalize_emoji(e):
            if not e:
                return ''
            # 使用 NFC 规范化
            normalized = unicodedata.normalize('NFC', e)
            # 移除变体选择符 (FE0E, FE0F) 和零宽连接符
            normalized = normalized.replace('\ufe0e', '').replace('\ufe0f', '').replace('\u200d', '')
            return normalized.strip()
        
        # 获取 emoji 的基础字符（只取第一个字符簇）
        def get_emoji_base(e):
            if not e:
                return ''
            # 移除所有修饰符
            cleaned = normalize_emoji(e)
            # 只取前面的主要表情（忽略肤色等修饰）
            if len(cleaned) > 0:
                # 返回第一个字符（对于简单 emoji）
                return cleaned[0] if len(cleaned) == 1 else cleaned[:2]
            return cleaned
        
        # 将选中的 emojis 规范化后存入多个格式以便匹配
        emoji_set = set()
        emoji_base_set = set()
        for e in emojis:
            normalized = normalize_emoji(e)
            base = get_emoji_base(e)
            emoji_set.add(normalized)
            emoji_set.add(e)  # 原始形式
            emoji_base_set.add(base)
            print(f"[DEBUG] 添加表情: 原始='{e}' 规范化='{normalized}' 基础='{base}' (bytes: {e.encode('unicode_escape')})")
        
        print(f"[DEBUG] 选中的表情集合: {emoji_set}")
        
        def get_emoji_count(msg):
            """计算消息中所有选中表情的反应总数"""
            total = 0
            reactions = msg.get('reactions', [])
            for r in reactions:
                original_emoji = r.get('emoji', '')
                normalized_emoji = normalize_emoji(original_emoji)
                base_emoji = get_emoji_base(original_emoji)
                count = r.get('count', 0)
                
                # 多种方式匹配
                matched = (
                    original_emoji in emoji_set or
                    normalized_emoji in emoji_set or
                    base_emoji in emoji_base_set
                )
                
                if matched:
                    total += count
                    # print(f"[DEBUG] 匹配到表情 {original_emoji}: +{count}")
            return total
        
        # 计算每个消息的指定表情反应总数
        for msg in messages:
            count = get_emoji_count(msg)
            msg['selected_emoji_count'] = count
        
        # 按选中表情的总反应数量降序排序
        sorted_messages = sorted(
            messages,
            key=lambda x: x.get('selected_emoji_count', 0),
            reverse=True
        )
        
        # Debug: 打印前10条消息的排序信息
        print(f"[DEBUG] 排序后前10条消息:")
        for i, msg in enumerate(sorted_messages[:10]):
            reactions_str = ', '.join([f"{r['emoji']}:{r['count']}" for r in msg.get('reactions', [])])
            print(f"  #{i+1}: selected_emoji_count={msg.get('selected_emoji_count', 0)}, reactions=[{reactions_str}]")
        
        return sorted_messages
    
    def start_analysis(self, channel, days, min_reactions, media_only, sort_by, emojis=None, date_from=None, date_to=None):
        """开始分析"""
        self.task_progress = {'status': 'running', 'progress': 0, 'message': '正在初始化...', 'data': None}
        
        asyncio.run_coroutine_threadsafe(
            self._analyze_async(channel, days, min_reactions, media_only, sort_by, emojis or [], date_from, date_to),
            self.loop
        )
        
        return {'success': True, 'message': '分析已开始'}


# 创建全局管理器
manager = TelegramManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    progress = manager.task_progress.copy()
    if progress.get('data') and 'all_messages' in progress['data']:
        progress['data'] = {k: v for k, v in progress['data'].items() if k != 'all_messages'}
    
    return jsonify({
        'is_logged_in': manager.is_logged_in,
        'user': manager.user_info,
        'phone': manager.phone,
        'awaiting_code': manager.phone_code_hash is not None and not manager.is_logged_in,
        'task': progress
    })


@app.route('/api/send_code', methods=['POST'])
def send_code():
    data = request.json
    phone = data.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'error': '请输入手机号'})
    
    return jsonify(manager.send_code(phone))


@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    data = request.json
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({'success': False, 'error': '请输入验证码'})
    
    if not manager.client or not manager.phone_code_hash:
        return jsonify({'success': False, 'error': '请先发送验证码'})
    
    return jsonify(manager.verify_code(code))


@app.route('/api/verify_password', methods=['POST'])
def verify_password():
    data = request.json
    password = data.get('password', '')
    
    if not password:
        return jsonify({'success': False, 'error': '请输入密码'})
    
    if not manager.client:
        return jsonify({'success': False, 'error': '请先发送验证码'})
    
    return jsonify(manager.verify_password(password))


@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.json or {}
    delete_session = data.get('delete_session', False)
    return jsonify(manager.logout(delete_session))


@app.route('/api/sessions')
def list_sessions():
    sessions = []
    for f in os.listdir('.'):
        if f.startswith('session_') and f.endswith('.session'):
            phone = f[8:-8]
            if len(phone) > 4:
                display = '+' + phone[:3] + '****' + phone[-4:]
            else:
                display = '+' + phone
            sessions.append({'file': f, 'phone': '+' + phone, 'display': display})
    return jsonify({'success': True, 'sessions': sessions})


@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    """删除指定的 session 文件"""
    data = request.json
    filename = data.get('filename', '')
    
    if not filename:
        return jsonify({'success': False, 'error': '缺少文件名'})
    
    # 安全检查
    if not filename.startswith('session_') or not filename.endswith('.session'):
        return jsonify({'success': False, 'error': '无效的文件名'})
    
    # 如果当前登录的是这个账号，先登出
    if manager.phone:
        current_session = manager.get_session_name(manager.phone) + '.session'
        if current_session == filename:
            manager.logout(delete_session=True)
            return jsonify({'success': True, 'message': '已登出并删除'})
    
    # 删除文件
    try:
        if os.path.exists(filename):
            os.remove(filename)
            return jsonify({'success': True, 'message': '已删除'})
        else:
            return jsonify({'success': False, 'error': '文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/dialogs')
def get_dialogs():
    if not manager.is_logged_in or not manager.fetcher:
        return jsonify({'success': False, 'error': '请先登录'})
    return jsonify(manager.get_dialogs())


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    if not manager.is_logged_in or not manager.fetcher:
        return jsonify({'success': False, 'error': '请先登录'})
    
    data = request.json
    channel = data.get('channel', '')
    days = int(data.get('days', 7))  # 默认7天
    date_from = data.get('date_from')  # 自定义开始日期
    date_to = data.get('date_to')  # 自定义结束日期
    min_reactions = int(data.get('min_reactions', 5))
    media_only = data.get('media_only', True)
    sort_by = data.get('sort_by', 'views')  # 默认按浏览量
    emojis = data.get('emojis', [])
    
    if not channel:
        return jsonify({'success': False, 'error': '请输入频道'})
    
    return jsonify(manager.start_analysis(channel, days, min_reactions, media_only, sort_by, emojis, date_from, date_to))


@app.route('/api/progress')
def get_progress():
    progress = manager.task_progress.copy()
    if progress.get('data') and 'all_messages' in progress['data']:
        progress['data'] = {k: v for k, v in progress['data'].items() if k != 'all_messages'}
    return jsonify(progress)


@app.route('/api/export', methods=['POST'])
def export_data():
    if manager.task_progress.get('status') != 'completed' or not manager.task_progress.get('data'):
        return jsonify({'success': False, 'error': '没有可导出的数据'})
    
    data = request.json
    format_type = data.get('format', 'json')
    
    try:
        exporter = Exporter()
        messages = manager.task_progress['data'].get('all_messages', manager.task_progress['data']['messages'])
        stats = manager.task_progress['data']['stats']
        
        if format_type == 'json':
            filepath = exporter.export_to_json(messages, include_stats=True, stats=stats)
        elif format_type == 'csv':
            filepath = exporter.export_to_csv(messages)
        else:
            return jsonify({'success': False, 'error': '不支持的格式'})
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, threaded=True)