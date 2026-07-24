package com.aira.mobile.data.source.local

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log

data class CallLogEntity(
    val sessionId: String,
    val callerNumber: String,
    val callerName: String,
    val status: String,
    val startTime: Long,
    val endTime: Long = 0,
    val durationSeconds: Int = 0,
    val isSimulation: Boolean = false,
    val ttftMs: Int = 0,
    val totalLatencyMs: Int = 0,
    val summaryText: String = "",
    val actionNeeded: String = ""
)

data class TranscriptEntity(
    val id: Int = 0,
    val sessionId: String,
    val speaker: String,
    val message: String,
    val timestamp: Long
)

class CallDatabaseHelper(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {
    companion object {
        private const val DATABASE_NAME = "aira_calls.db"
        private const val DATABASE_VERSION = 5
        private const val TAG = "CallDatabaseHelper"

        // Table Names
        private const val TABLE_CALL_LOGS = "call_logs"
        private const val TABLE_TRANSCRIPTS = "transcripts"

        // Call Logs Columns
        private const val COL_CALL_SESSION_ID = "session_id"
        private const val COL_CALL_NUMBER = "caller_number"
        private const val COL_CALL_NAME = "caller_name"
        private const val COL_CALL_STATUS = "status"
        private const val COL_CALL_START_TIME = "start_time"
        private const val COL_CALL_END_TIME = "end_time"
        private const val COL_CALL_DURATION = "duration_seconds"
        private const val COL_CALL_IS_SIMULATION = "is_simulation"
        private const val COL_CALL_TTFT_MS = "ttft_ms"
        private const val COL_CALL_TOTAL_LATENCY_MS = "total_latency_ms"
        private const val COL_CALL_SUMMARY_TEXT = "summary_text"
        private const val COL_CALL_ACTION_NEEDED = "action_needed"

        // Transcripts Columns
        private const val COL_TRANS_ID = "id"
        private const val COL_TRANS_SESSION_ID = "session_id"
        private const val COL_TRANS_SPEAKER = "speaker"
        private const val COL_TRANS_MESSAGE = "message"
        private const val COL_TRANS_TIMESTAMP = "timestamp"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val createCallLogsTable = """
            CREATE TABLE $TABLE_CALL_LOGS (
                $COL_CALL_SESSION_ID TEXT PRIMARY KEY,
                $COL_CALL_NUMBER TEXT,
                $COL_CALL_NAME TEXT,
                $COL_CALL_STATUS TEXT,
                $COL_CALL_START_TIME INTEGER,
                $COL_CALL_END_TIME INTEGER,
                $COL_CALL_DURATION INTEGER,
                $COL_CALL_IS_SIMULATION INTEGER DEFAULT 0,
                $COL_CALL_TTFT_MS INTEGER DEFAULT 0,
                $COL_CALL_TOTAL_LATENCY_MS INTEGER DEFAULT 0,
                $COL_CALL_SUMMARY_TEXT TEXT DEFAULT '',
                $COL_CALL_ACTION_NEEDED TEXT DEFAULT ''
            )
        """.trimIndent()

        val createTranscriptsTable = """
            CREATE TABLE $TABLE_TRANSCRIPTS (
                $COL_TRANS_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                $COL_TRANS_SESSION_ID TEXT,
                $COL_TRANS_SPEAKER TEXT,
                $COL_TRANS_MESSAGE TEXT,
                $COL_TRANS_TIMESTAMP INTEGER,
                FOREIGN KEY($COL_TRANS_SESSION_ID) REFERENCES $TABLE_CALL_LOGS($COL_CALL_SESSION_ID) ON DELETE CASCADE
            )
        """.trimIndent()

        db.execSQL(createCallLogsTable)
        db.execSQL(createTranscriptsTable)
        Log.i(TAG, "Database tables created")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_TRANSCRIPTS")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_CALL_LOGS")
        onCreate(db)
    }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.setForeignKeyConstraintsEnabled(true)
    }

    // Insert or update call log
    fun insertCallLog(callLog: CallLogEntity) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_CALL_SESSION_ID, callLog.sessionId)
            put(COL_CALL_NUMBER, callLog.callerNumber)
            put(COL_CALL_NAME, callLog.callerName)
            put(COL_CALL_STATUS, callLog.status)
            put(COL_CALL_START_TIME, callLog.startTime)
            put(COL_CALL_END_TIME, callLog.endTime)
            put(COL_CALL_DURATION, callLog.durationSeconds)
            put(COL_CALL_IS_SIMULATION, if (callLog.isSimulation) 1 else 0)
            put(COL_CALL_TTFT_MS, callLog.ttftMs)
            put(COL_CALL_TOTAL_LATENCY_MS, callLog.totalLatencyMs)
            put(COL_CALL_SUMMARY_TEXT, callLog.summaryText)
            put(COL_CALL_ACTION_NEEDED, callLog.actionNeeded)
        }
        db.insertWithOnConflict(TABLE_CALL_LOGS, null, values, SQLiteDatabase.CONFLICT_REPLACE)
    }

    fun updateCallEnd(sessionId: String, endTime: Long, durationSeconds: Int, status: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_CALL_END_TIME, endTime)
            put(COL_CALL_DURATION, durationSeconds)
            put(COL_CALL_STATUS, status)
        }
        db.update(TABLE_CALL_LOGS, values, "$COL_CALL_SESSION_ID = ?", arrayOf(sessionId))
    }

    fun updateCallTtft(sessionId: String, ttftMs: Int) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_CALL_TTFT_MS, ttftMs)
        }
        db.update(TABLE_CALL_LOGS, values, "$COL_CALL_SESSION_ID = ?", arrayOf(sessionId))
        Log.i(TAG, "Updated call TTFT for session: $sessionId to $ttftMs ms")
    }

    fun updateCallMetrics(sessionId: String, ttftMs: Int, totalLatencyMs: Int) {
        val db = writableDatabase
        val values = ContentValues().apply {
            if (ttftMs > 0) put(COL_CALL_TTFT_MS, ttftMs)
            if (totalLatencyMs > 0) put(COL_CALL_TOTAL_LATENCY_MS, totalLatencyMs)
        }
        db.update(TABLE_CALL_LOGS, values, "$COL_CALL_SESSION_ID = ?", arrayOf(sessionId))
        Log.i(TAG, "Updated call metrics for session: $sessionId to TTFT=$ttftMs ms, Total=$totalLatencyMs ms")
    }

    // Insert transcript
    fun insertTranscript(transcript: TranscriptEntity) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_TRANS_SESSION_ID, transcript.sessionId)
            put(COL_TRANS_SPEAKER, transcript.speaker)
            put(COL_TRANS_MESSAGE, transcript.message)
            put(COL_TRANS_TIMESTAMP, transcript.timestamp)
        }
        db.insert(TABLE_TRANSCRIPTS, null, values)
    }

    // Query all call logs
    fun getAllCallLogs(): List<CallLogEntity> {
        val list = mutableListOf<CallLogEntity>()
        val db = readableDatabase
        val query = "SELECT * FROM $TABLE_CALL_LOGS ORDER BY $COL_CALL_START_TIME DESC"
        val cursor = db.rawQuery(query, null)
        if (cursor.moveToFirst()) {
            do {
                val sessionId = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_SESSION_ID))
                val number = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_NUMBER))
                val name = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_NAME))
                val status = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_STATUS))
                val startTime = cursor.getLong(cursor.getColumnIndexOrThrow(COL_CALL_START_TIME))
                val endTime = cursor.getLong(cursor.getColumnIndexOrThrow(COL_CALL_END_TIME))
                val duration = cursor.getInt(cursor.getColumnIndexOrThrow(COL_CALL_DURATION))
                val isSim = cursor.getInt(cursor.getColumnIndexOrThrow(COL_CALL_IS_SIMULATION)) == 1
                val ttft = cursor.getInt(cursor.getColumnIndexOrThrow(COL_CALL_TTFT_MS))
                val totalLat = cursor.getInt(cursor.getColumnIndexOrThrow(COL_CALL_TOTAL_LATENCY_MS))
                val summaryText = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_SUMMARY_TEXT)) ?: ""
                val actionNeeded = cursor.getString(cursor.getColumnIndexOrThrow(COL_CALL_ACTION_NEEDED)) ?: ""
                list.add(CallLogEntity(sessionId, number, name, status, startTime, endTime, duration, isSim, ttft, totalLat, summaryText, actionNeeded))
            } while (cursor.moveToNext())
        }
        cursor.close()
        return list
    }

    // Query transcripts for a session
    fun getTranscriptsForSession(sessionId: String): List<TranscriptEntity> {
        val list = mutableListOf<TranscriptEntity>()
        val db = readableDatabase
        val query = "SELECT * FROM $TABLE_TRANSCRIPTS WHERE $COL_TRANS_SESSION_ID = ? ORDER BY $COL_TRANS_TIMESTAMP ASC"
        val cursor = db.rawQuery(query, arrayOf(sessionId))
        if (cursor.moveToFirst()) {
            do {
                val id = cursor.getInt(cursor.getColumnIndexOrThrow(COL_TRANS_ID))
                val speaker = cursor.getString(cursor.getColumnIndexOrThrow(COL_TRANS_SPEAKER))
                val msg = cursor.getString(cursor.getColumnIndexOrThrow(COL_TRANS_MESSAGE))
                val time = cursor.getLong(cursor.getColumnIndexOrThrow(COL_TRANS_TIMESTAMP))
                list.add(TranscriptEntity(id, sessionId, speaker, msg, time))
            } while (cursor.moveToNext())
        }
        cursor.close()
        return list
    }

    // Sync transcripts from server (which contain both original and English translation) into local SQLite
    fun syncTranscripts(sessionId: String, transcripts: List<TranscriptEntity>) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.delete(TABLE_TRANSCRIPTS, "$COL_TRANS_SESSION_ID = ?", arrayOf(sessionId))
            for (t in transcripts) {
                val values = ContentValues().apply {
                    put(COL_TRANS_SESSION_ID, t.sessionId)
                    put(COL_TRANS_SPEAKER, t.speaker)
                    put(COL_TRANS_MESSAGE, t.message)
                    put(COL_TRANS_TIMESTAMP, t.timestamp)
                }
                db.insert(TABLE_TRANSCRIPTS, null, values)
            }
            db.setTransactionSuccessful()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to sync transcripts for session $sessionId: ${e.message}", e)
        } finally {
            db.endTransaction()
        }
    }
}
