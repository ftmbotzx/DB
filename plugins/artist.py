from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict
from datetime import datetime, timedelta
import pytz


from database.db import db


from datetime import datetime, timedelta, timezone
import re

def parse_datetime_with_tz(datetime_str):
    match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([+-])(\d{2})(\d{2})", datetime_str)
    if match:
        dt_part, sign, hours_offset, minutes_offset = match.groups()
        dt = datetime.strptime(dt_part, "%Y-%m-%d %H:%M:%S")
        offset = timedelta(hours=int(hours_offset), minutes=int(minutes_offset))
        if sign == '-':
            offset = -offset
        tz = timezone(offset)
        return dt.replace(tzinfo=tz)
    return None


async def generate_monitor_text():
    tasks = await db.tasks_collection.find().to_list(length=1000)
    bots = await db.bots.find({"active": True}).to_list(None)

    if not tasks and not bots:
        return "📭 No bots or tasks found yet."

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    text = "📊 **Current Task Status**\n\n"

    bot_statuses = defaultdict(lambda: {"status": None, "sent": 0, "skipped": 0, "failed": 0, "updated_at": None})
    total_sent = total_skipped = total_failed = 0
    latest_time = None
    earliest_time = None

    for task in tasks:
        bot_id = task.get("bot_name", "N/A")
        status = task.get("status", "N/A").capitalize()
        sent = task.get("sent_count", 0)
        skipped = task.get("skipped_count", 0)
        failed = task.get("failed_count", 0)
        updated = task.get("updated_at") or task.get("assigned_at")

        updated_dt = None
        if updated:
            if isinstance(updated, str):
                updated_dt = parse_datetime_with_tz(updated)
            else:
                updated_dt = updated
            if updated_dt:
                if updated_dt.tzinfo is None:
                    updated_dt = ist.localize(updated_dt)
                else:
                    updated_dt = updated_dt.astimezone(ist)

        if updated_dt:
            if not earliest_time or updated_dt < earliest_time:
                earliest_time = updated_dt
            if not latest_time or updated_dt > latest_time:
                latest_time = updated_dt

        bot_statuses[bot_id]["status"] = status
        bot_statuses[bot_id]["sent"] = sent
        bot_statuses[bot_id]["skipped"] = skipped
        bot_statuses[bot_id]["failed"] = failed
        bot_statuses[bot_id]["updated_at"] = updated_dt

        total_sent += sent
        total_skipped += skipped
        total_failed += failed

    total_bots_from_tasks = len(bot_statuses)
    total_active_bots = len(bots)
    running_tasks_count = 0

    for bot_id, data in bot_statuses.items():
        status = data['status']
        updated_at = data['updated_at']

        too_old = False
        if updated_at:
            diff = now - updated_at
            if diff > timedelta(minutes=30):
                too_old = True

        if status and status.lower() == "running" and not too_old:
            status_icon = "✅"
            running_tasks_count += 1
        else:
            status_icon = "❌"

        updated_str = updated_at.strftime("%d %b %Y %I:%M %p") if updated_at else "N/A"

        text += (
            f"🤖 **Bot ID**: `{bot_id}` | Status: **{status} {status_icon}** | "
            f"Last Updated: `{updated_str}`\n\n"
        )

    text += (
        f"\n📦 **Total Bots (active in DB):** {total_active_bots}\n"
        f"🤖 **Bots with Tasks:** {total_bots_from_tasks}\n"
        f"🏃‍♂️ **Running Tasks:** {running_tasks_count}\n"
        f"📤 **Total Sent:** {total_sent}\n"
        f"⏭️ **Total Skipped:** {total_skipped}\n"
        f"❌ **Total Failed:** {total_failed}\n"
    )

    # Add speed & elapsed time if possible
    if earliest_time and latest_time and latest_time > earliest_time:
        total_minutes = (latest_time - earliest_time).total_seconds() / 60
        if total_minutes > 0:
            per_min_speed = total_sent / total_minutes
            per_day_est = int(per_min_speed * 1440)

            elapsed = latest_time - earliest_time
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            time_elapsed_str = f"{elapsed.days * 24 + hours} hr {minutes} min"

            text += (
                f"\n🚀 **Speed**: {per_min_speed:.2f}/min (~{per_day_est:,}/day)\n"
                f"⏱️ **Time Elapsed:** {time_elapsed_str}\n"
            )

    return text



@Client.on_message(filters.command("monitor") & filters.private)
async def monitor_tasks(client, message):
    text = await generate_monitor_text()

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📂 View Track", callback_data="view_track_files_summary"),
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_monitor")
            ]
        ]
    )

    await message.reply(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex("view_track_files_summary"))
async def show_track_files_summary(client, callback_query):
    assigned_count = await db.track_files.count_documents({"assigned": True})
    unassigned_count = await db.track_files.count_documents({"assigned": False})
    total_files = assigned_count + unassigned_count

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_tracks": {"$sum": "$total_tracks"},
                "assigned_tracks": {
                    "$sum": {
                        "$cond": [{"$eq": ["$assigned", True]}, "$total_tracks", 0]
                    }
                },
                "unassigned_tracks": {
                    "$sum": {
                        "$cond": [{"$eq": ["$assigned", False]}, "$total_tracks", 0]
                    }
                }
            }
        }
    ]

    agg_result = await db.track_files.aggregate(pipeline).to_list(length=1)
    if agg_result:
        total_tracks = agg_result[0].get("total_tracks", 0)
        assigned_tracks = agg_result[0].get("assigned_tracks", 0)
        unassigned_tracks = agg_result[0].get("unassigned_tracks", 0)
    else:
        total_tracks = assigned_tracks = unassigned_tracks = 0

    text = (
        f"📂 Track Files Summary:\n\n"
        f"📁 Total Files: {total_files}\n"
        f"✅ Assigned Files: {assigned_count}\n"
        f"📭 Unassigned Files: {unassigned_count}\n"
        f"🎼 Total Tracks: {total_tracks}\n"
        f"📌 Assigned Tracks: {assigned_tracks}\n"
        f"📤 Unassigned Tracks: {unassigned_tracks}"
    )

    await callback_query.answer(text, show_alert=True)



@Client.on_callback_query(filters.regex("refresh_monitor"))
async def refresh_monitor(client, callback_query):
    text = await generate_monitor_text()
    await callback_query.answer("Refreshed ✅", show_alert=False)
    await callback_query.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📂 View Track", callback_data="view_track_files_summary"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh_monitor")
                ]
            ]
        )
    )
