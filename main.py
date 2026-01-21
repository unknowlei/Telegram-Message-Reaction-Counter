#!/usr/bin/env python3
"""
Telegram Reaction Counter - 主程序入口

统计 Telegram 频道/群组消息的反应数量，找出最热门的内容。

使用方法:
    python main.py                  # 使用配置文件中的设置
    python main.py --channel @xxx   # 指定频道
    python main.py --limit 500      # 限制消息数量
    python main.py --list           # 列出已加入的频道/群组
"""

import asyncio
import argparse
import sys
from datetime import datetime

# 导入自定义模块
import config
from fetcher import TelegramFetcher
from analyzer import MessageAnalyzer, print_top_messages, print_statistics
from exporter import Exporter, ReportGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Telegram 频道/群组反应统计工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                          使用配置文件中的设置运行
  python main.py --channel @game_channel  统计指定频道
  python main.py --limit 500              只获取最近 500 条消息
  python main.py --list                   列出你加入的频道/群组
  python main.py --no-media               包含所有消息（不仅限于媒体消息）
  python main.py --min-reactions 10       只统计反应数 >= 10 的消息
  python main.py --export json            只导出 JSON 格式
  python main.py --report                 生成 Markdown/HTML 报告
        """
    )
    
    parser.add_argument(
        '--channel', '-c',
        type=str,
        help='目标频道/群组（用户名、链接或 ID）'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=config.MAX_MESSAGES,
        help=f'获取的最大消息数量（默认: {config.MAX_MESSAGES}）'
    )
    
    parser.add_argument(
        '--min-reactions', '-m',
        type=int,
        default=config.MIN_REACTIONS,
        help=f'最小反应数阈值（默认: {config.MIN_REACTIONS}）'
    )
    
    parser.add_argument(
        '--no-media',
        action='store_true',
        help='包含所有消息，不仅限于媒体消息'
    )
    
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=config.TOP_N_DISPLAY,
        help=f'显示 Top N 消息（默认: {config.TOP_N_DISPLAY}）'
    )
    
    parser.add_argument(
        '--export', '-e',
        choices=['json', 'csv', 'both', 'none'],
        default=config.OUTPUT_FORMAT,
        help=f'导出格式（默认: {config.OUTPUT_FORMAT}）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=config.OUTPUT_FILENAME,
        help=f'输出文件名（不含扩展名，默认: {config.OUTPUT_FILENAME}）'
    )
    
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='生成 Markdown 和 HTML 报告'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出你加入的频道/群组'
    )
    
    parser.add_argument(
        '--sort-by',
        choices=['reactions', 'views', 'engagement'],
        default='reactions',
        help='排序依据（默认: reactions）'
    )
    
    parser.add_argument(
        '--filter-type',
        type=str,
        help='按媒体类型过滤，多个类型用逗号分隔（如: archive,video）'
    )
    
    parser.add_argument(
        '--keyword', '-k',
        type=str,
        help='按关键词过滤，多个关键词用逗号分隔'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help='只统计最近 N 天的消息'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，减少输出'
    )
    
    return parser.parse_args()


async def list_dialogs(fetcher: TelegramFetcher):
    """列出用户加入的频道/群组"""
    print("\n" + "=" * 60)
    print("  你加入的频道/群组")
    print("=" * 60 + "\n")
    
    dialogs = await fetcher.list_dialogs(50)
    
    # 分类
    channels = [d for d in dialogs if d['is_channel']]
    groups = [d for d in dialogs if not d['is_channel']]
    
    if channels:
        print("📢 频道:")
        for i, d in enumerate(channels, 1):
            username = f" (@{d['username']})" if d['username'] else ""
            print(f"   {i}. {d['name']}{username}")
        print()
    
    if groups:
        print("👥 群组:")
        for i, d in enumerate(groups, 1):
            username = f" (@{d['username']})" if d['username'] else ""
            print(f"   {i}. {d['name']}{username}")
        print()
    
    print(f"共计: {len(channels)} 个频道, {len(groups)} 个群组")
    print()
    print("提示: 使用 --channel 参数指定要统计的频道/群组")
    print("例如: python main.py --channel @channel_name")


async def run_analysis(args):
    """运行分析"""
    fetcher = TelegramFetcher()
    
    try:
        # 连接
        await fetcher.connect()
        
        # 如果是列出对话模式
        if args.list:
            await list_dialogs(fetcher)
            return
        
        # 确定目标频道
        target = args.channel or config.TARGET_CHANNEL
        if not target or target == "your_channel_username":
            print("\n⚠ 错误: 请指定目标频道/群组")
            print("  使用 --channel 参数指定，或在 config.py 中配置 TARGET_CHANNEL")
            print("  使用 --list 查看你加入的频道/群组")
            return
        
        # 获取频道
        if not await fetcher.get_channel(target):
            return
        
        print()
        
        # 获取消息
        messages = await fetcher.fetch_messages(
            limit=args.limit,
            min_reactions=args.min_reactions,
            media_only=not args.no_media
        )
        
        if not messages:
            print("\n⚠ 没有找到符合条件的消息")
            return
        
        # 创建分析器
        analyzer = MessageAnalyzer(messages)
        
        # 应用过滤器
        filtered_messages = messages
        
        # 按媒体类型过滤
        if args.filter_type:
            types = [t.strip() for t in args.filter_type.split(',')]
            filtered_messages = analyzer.filter_by_media_type(types, filtered_messages)
            print(f"按媒体类型过滤后: {len(filtered_messages)} 条消息")
        
        # 按关键词过滤
        if args.keyword:
            keywords = [k.strip() for k in args.keyword.split(',')]
            filtered_messages = analyzer.filter_by_keyword(keywords, messages=filtered_messages)
            print(f"按关键词过滤后: {len(filtered_messages)} 条消息")
        
        # 按日期过滤
        if args.days:
            filtered_messages = analyzer.filter_by_date_range(days=args.days, messages=filtered_messages)
            print(f"按日期过滤后: {len(filtered_messages)} 条消息")
        
        if not filtered_messages:
            print("\n⚠ 过滤后没有消息")
            return
        
        # 更新分析器的消息列表
        analyzer.messages = filtered_messages
        
        # 排序
        if args.sort_by == 'views':
            sorted_messages = analyzer.sort_by_views()
        elif args.sort_by == 'engagement':
            sorted_messages = analyzer.sort_by_engagement_rate()
        else:
            sorted_messages = analyzer.sort_by_reactions()
        
        # 生成统计
        stats = analyzer.generate_summary()
        
        # 打印结果
        if not args.quiet:
            print_top_messages(sorted_messages, n=args.top)
            print_statistics(stats)
        
        # 导出
        if args.export != 'none':
            exporter = Exporter()
            exported = exporter.export_all(
                sorted_messages,
                stats=stats,
                filename=args.output,
                format=args.export
            )
            print(f"\n导出完成:")
            for format_type, path in exported.items():
                print(f"  {format_type.upper()}: {path}")
        
        # 生成报告
        if args.report:
            report_gen = ReportGenerator()
            
            md_path = report_gen.generate_markdown_report(
                sorted_messages,
                stats,
                fetcher.channel_info,
                filename=args.output
            )
            
            html_path = report_gen.generate_html_report(
                sorted_messages,
                stats,
                fetcher.channel_info,
                filename=args.output
            )
            
            print(f"\n报告生成完成:")
            print(f"  Markdown: {md_path}")
            print(f"  HTML: {html_path}")
        
        print("\n✓ 分析完成!")
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断操作")
    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        raise
    finally:
        await fetcher.disconnect()


def check_config():
    """检查配置是否正确"""
    errors = []
    
    if config.API_ID == 12345678:
        errors.append("API_ID 未配置（请在 config.py 中设置）")
    
    if config.API_HASH == "your_api_hash_here":
        errors.append("API_HASH 未配置（请在 config.py 中设置）")
    
    if errors:
        print("\n" + "=" * 60)
        print("  ⚠ 配置检查失败")
        print("=" * 60)
        print()
        for error in errors:
            print(f"  ✗ {error}")
        print()
        print("请先完成以下步骤:")
        print("  1. 访问 https://my.telegram.org")
        print("  2. 使用手机号登录")
        print("  3. 创建应用获取 API ID 和 API Hash")
        print("  4. 将获取的值填入 config.py 文件")
        print()
        return False
    
    return True


def print_banner():
    """打印启动 Banner"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   📊 Telegram Reaction Counter                             ║
║                                                            ║
║   统计 Telegram 频道/群组的反应数据，找出最热门的内容     ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    args = parse_args()
    
    if not args.quiet:
        print_banner()
    
    # 检查配置
    if not check_config():
        sys.exit(1)
    
    # 运行
    asyncio.run(run_analysis(args))


if __name__ == "__main__":
    main()