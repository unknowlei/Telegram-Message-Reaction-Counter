"""
结果导出模块

负责将分析结果导出为 JSON、CSV 等格式
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

import config


class Exporter:
    """数据导出器"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录，默认使用配置值
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"已创建输出目录: {self.output_dir}")
    
    def _serialize_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        序列化消息数据（处理日期等不可直接序列化的类型）
        
        Args:
            msg: 消息数据
            
        Returns:
            dict: 可序列化的消息数据
        """
        serialized = msg.copy()
        
        # 转换日期
        if 'date' in serialized and serialized['date']:
            serialized['date'] = serialized['date'].isoformat()
        
        return serialized
    
    def export_to_json(
        self,
        data: List[Dict[str, Any]],
        filename: str = None,
        include_stats: bool = False,
        stats: Dict[str, Any] = None
    ) -> str:
        """
        导出为 JSON 格式
        
        Args:
            data: 消息数据列表
            filename: 文件名（不含扩展名）
            include_stats: 是否包含统计数据
            stats: 统计数据
            
        Returns:
            str: 导出的文件路径
        """
        filename = filename or config.OUTPUT_FILENAME
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        # 序列化消息
        serialized_data = [self._serialize_message(msg) for msg in data]
        
        # 构建输出数据
        output = {
            'exported_at': datetime.now().isoformat(),
            'total_messages': len(serialized_data),
            'messages': serialized_data,
        }
        
        # 添加统计数据
        if include_stats and stats:
            # 处理统计数据中的日期
            stats_copy = stats.copy()
            if 'date_range' in stats_copy:
                date_range = stats_copy['date_range']
                if date_range.get('start'):
                    date_range['start'] = date_range['start'].isoformat()
                if date_range.get('end'):
                    date_range['end'] = date_range['end'].isoformat()
            output['statistics'] = stats_copy
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已导出 JSON: {filepath}")
        return filepath
    
    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        filename: str = None,
        include_reactions: bool = True
    ) -> str:
        """
        导出为 CSV 格式
        
        Args:
            data: 消息数据列表
            filename: 文件名（不含扩展名）
            include_reactions: 是否包含详细反应
            
        Returns:
            str: 导出的文件路径
        """
        filename = filename or config.OUTPUT_FILENAME
        filepath = os.path.join(self.output_dir, f"{filename}.csv")
        
        # 定义字段
        fieldnames = [
            'rank',
            'id',
            'date',
            'total_reactions',
            'views',
            'forwards',
            'media_type',
            'filename',
            'file_size_mb',
            'text_preview',
            'link',
        ]
        
        if include_reactions:
            fieldnames.append('reactions_detail')
        
        # 写入 CSV
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, msg in enumerate(data, 1):
                # 处理文本预览
                text = msg.get('text') or ''
                text_preview = (text[:100] + '...') if len(text) > 100 else text
                text_preview = text_preview.replace('\n', ' ').replace('\r', '')
                
                # 处理日期
                date_str = ''
                if msg.get('date'):
                    date_str = msg['date'].strftime('%Y-%m-%d %H:%M:%S')
                
                # 处理文件大小
                file_size_mb = ''
                if msg['media'].get('size'):
                    file_size_mb = f"{msg['media']['size'] / (1024*1024):.2f}"
                
                row = {
                    'rank': i,
                    'id': msg['id'],
                    'date': date_str,
                    'total_reactions': msg['total_reactions'],
                    'views': msg.get('views') or '',
                    'forwards': msg.get('forwards') or '',
                    'media_type': msg['media'].get('type') or '',
                    'filename': msg['media'].get('filename') or '',
                    'file_size_mb': file_size_mb,
                    'text_preview': text_preview,
                    'link': msg['link'],
                }
                
                if include_reactions:
                    reactions_str = ', '.join(
                        f"{r['emoji']}:{r['count']}" for r in msg['reactions']
                    )
                    row['reactions_detail'] = reactions_str
                
                writer.writerow(row)
        
        print(f"✓ 已导出 CSV: {filepath}")
        return filepath
    
    def export_stats_to_json(
        self,
        stats: Dict[str, Any],
        filename: str = None
    ) -> str:
        """
        单独导出统计数据为 JSON
        
        Args:
            stats: 统计数据
            filename: 文件名
            
        Returns:
            str: 导出的文件路径
        """
        filename = filename or f"{config.OUTPUT_FILENAME}_stats"
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        # 处理日期
        stats_copy = stats.copy()
        if 'date_range' in stats_copy:
            date_range = stats_copy['date_range']
            if date_range.get('start'):
                date_range['start'] = date_range['start'].isoformat()
            if date_range.get('end'):
                date_range['end'] = date_range['end'].isoformat()
        
        output = {
            'exported_at': datetime.now().isoformat(),
            'statistics': stats_copy,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已导出统计数据: {filepath}")
        return filepath
    
    def export_all(
        self,
        data: List[Dict[str, Any]],
        stats: Dict[str, Any] = None,
        filename: str = None,
        format: str = None
    ) -> Dict[str, str]:
        """
        根据配置导出所有格式
        
        Args:
            data: 消息数据列表
            stats: 统计数据
            filename: 文件名
            format: 导出格式，可选 'json', 'csv', 'both'
            
        Returns:
            dict: 导出的文件路径字典
        """
        format = format or config.OUTPUT_FORMAT
        filename = filename or config.OUTPUT_FILENAME
        
        exported = {}
        
        if format in ('json', 'both'):
            exported['json'] = self.export_to_json(
                data,
                filename,
                include_stats=True,
                stats=stats
            )
        
        if format in ('csv', 'both'):
            exported['csv'] = self.export_to_csv(data, filename)
        
        return exported


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_markdown_report(
        self,
        messages: List[Dict[str, Any]],
        stats: Dict[str, Any],
        channel_info: Dict[str, Any],
        filename: str = None
    ) -> str:
        """
        生成 Markdown 格式报告
        
        Args:
            messages: 消息列表
            stats: 统计数据
            channel_info: 频道信息
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        filename = filename or f"{config.OUTPUT_FILENAME}_report"
        filepath = os.path.join(self.output_dir, f"{filename}.md")
        
        lines = []
        
        # 标题
        lines.append(f"# 📊 Telegram 频道反应统计报告")
        lines.append("")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 频道信息
        lines.append("## 📢 频道信息")
        lines.append("")
        lines.append(f"- **名称**: {channel_info.get('title', 'N/A')}")
        if channel_info.get('username'):
            lines.append(f"- **用户名**: @{channel_info['username']}")
        lines.append(f"- **类型**: {'频道' if channel_info.get('is_channel') else '群组'}")
        lines.append("")
        
        # 统计概览
        lines.append("## 📈 统计概览")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 分析消息数 | {stats['total_messages']} |")
        lines.append(f"| 总反应数 | {stats['total_reactions']} |")
        lines.append(f"| 总浏览量 | {stats['total_views']} |")
        lines.append(f"| 平均反应 | {stats['avg_reactions']:.1f} |")
        lines.append(f"| 平均浏览 | {stats['avg_views']:.1f} |")
        lines.append("")
        
        # 热门表情
        reaction_stats = stats.get('reaction_stats', {})
        if reaction_stats.get('top_emojis'):
            lines.append("## 🎭 热门表情 Top 10")
            lines.append("")
            lines.append("| 排名 | 表情 | 使用次数 |")
            lines.append("|------|------|----------|")
            for i, (emoji, count) in enumerate(reaction_stats['top_emojis'][:10], 1):
                lines.append(f"| {i} | {emoji} | {count} |")
            lines.append("")
        
        # 媒体类型统计
        media_stats = stats.get('media_stats', {})
        if media_stats.get('type_counts'):
            lines.append("## 📁 媒体类型分布")
            lines.append("")
            lines.append("| 类型 | 数量 | 平均反应 |")
            lines.append("|------|------|----------|")
            for mtype, count in media_stats['type_counts'].items():
                avg = media_stats['type_average'].get(mtype, 0)
                lines.append(f"| {mtype} | {count} | {avg:.1f} |")
            lines.append("")
        
        # Top 消息列表
        lines.append(f"## 🔥 Top {min(50, len(messages))} 热门消息")
        lines.append("")
        
        for i, msg in enumerate(messages[:50], 1):
            lines.append(f"### #{i} - {msg['total_reactions']} 反应")
            lines.append("")
            
            # 消息内容
            if msg.get('text'):
                text = msg['text'][:200] + ('...' if len(msg['text']) > 200 else '')
                text = text.replace('\n', ' ')
                lines.append(f"> {text}")
                lines.append("")
            
            # 媒体信息
            media = msg['media']
            if media['has_media']:
                media_info = f"📎 **{media['type']}**"
                if media['filename']:
                    media_info += f": {media['filename']}"
                if media['size']:
                    size_mb = media['size'] / (1024 * 1024)
                    media_info += f" ({size_mb:.1f} MB)"
                lines.append(media_info)
                lines.append("")
            
            # 反应详情
            reactions_str = ' '.join(f"{r['emoji']}×{r['count']}" for r in msg['reactions'])
            lines.append(f"💬 {reactions_str}")
            lines.append("")
            
            # 链接
            lines.append(f"🔗 [{msg['link']}]({msg['link']})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ 已生成报告: {filepath}")
        return filepath
    
    def generate_html_report(
        self,
        messages: List[Dict[str, Any]],
        stats: Dict[str, Any],
        channel_info: Dict[str, Any],
        filename: str = None
    ) -> str:
        """
        生成 HTML 格式报告
        
        Args:
            messages: 消息列表
            stats: 统计数据
            channel_info: 频道信息
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        filename = filename or f"{config.OUTPUT_FILENAME}_report"
        filepath = os.path.join(self.output_dir, f"{filename}.html")
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram 反应统计报告 - {channel_info.get('title', 'N/A')}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{ color: #0088cc; border-bottom: 2px solid #0088cc; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #0088cc;
        }}
        .stat-card .label {{
            color: #666;
            margin-top: 5px;
        }}
        .message-card {{
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .message-card .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .message-card .rank {{
            font-size: 1.5em;
            font-weight: bold;
            color: #0088cc;
        }}
        .message-card .reactions {{
            font-size: 1.2em;
            color: #ff6b6b;
        }}
        .message-card .content {{
            color: #666;
            margin: 10px 0;
            line-height: 1.5;
        }}
        .message-card .media {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .message-card .emoji-row {{
            font-size: 1.1em;
            margin: 10px 0;
        }}
        .message-card .link {{
            color: #0088cc;
            text-decoration: none;
        }}
        .message-card .link:hover {{
            text-decoration: underline;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{ background: #0088cc; color: white; }}
        tr:hover {{ background: #f8f9fa; }}
        .emoji-table td:first-child {{ font-size: 1.5em; }}
    </style>
</head>
<body>
    <h1>📊 Telegram 频道反应统计报告</h1>
    <p>频道: <strong>{channel_info.get('title', 'N/A')}</strong> | 
       生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>📈 统计概览</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{stats['total_messages']}</div>
            <div class="label">分析消息数</div>
        </div>
        <div class="stat-card">
            <div class="value">{stats['total_reactions']}</div>
            <div class="label">总反应数</div>
        </div>
        <div class="stat-card">
            <div class="value">{stats['total_views']}</div>
            <div class="label">总浏览量</div>
        </div>
        <div class="stat-card">
            <div class="value">{stats['avg_reactions']:.1f}</div>
            <div class="label">平均反应</div>
        </div>
    </div>
"""
        
        # 热门表情
        reaction_stats = stats.get('reaction_stats', {})
        if reaction_stats.get('top_emojis'):
            html += """
    <h2>🎭 热门表情</h2>
    <table class="emoji-table">
        <tr><th>表情</th><th>使用次数</th></tr>
"""
            for emoji, count in reaction_stats['top_emojis'][:10]:
                html += f"        <tr><td>{emoji}</td><td>{count}</td></tr>\n"
            html += "    </table>\n"
        
        # Top 消息
        html += f"""
    <h2>🔥 Top {min(50, len(messages))} 热门消息</h2>
"""
        
        for i, msg in enumerate(messages[:50], 1):
            text = msg.get('text', '')[:200] + ('...' if len(msg.get('text', '')) > 200 else '')
            text = text.replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
            
            media_html = ""
            if msg['media']['has_media']:
                media_info = f"📎 {msg['media']['type']}"
                if msg['media']['filename']:
                    media_info += f": {msg['media']['filename']}"
                if msg['media']['size']:
                    size_mb = msg['media']['size'] / (1024 * 1024)
                    media_info += f" ({size_mb:.1f} MB)"
                media_html = f'<div class="media">{media_info}</div>'
            
            reactions_html = ' '.join(f"{r['emoji']}×{r['count']}" for r in msg['reactions'])
            
            html += f"""
    <div class="message-card">
        <div class="header">
            <span class="rank">#{i}</span>
            <span class="reactions">🔥 {msg['total_reactions']} 反应</span>
        </div>
        <div class="content">{text if text else '[媒体文件]'}</div>
        {media_html}
        <div class="emoji-row">💬 {reactions_html}</div>
        <a href="{msg['link']}" target="_blank" class="link">🔗 查看原消息</a>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ 已生成 HTML 报告: {filepath}")
        return filepath