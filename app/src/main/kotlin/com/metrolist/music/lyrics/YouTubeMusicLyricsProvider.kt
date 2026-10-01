/**
 * Metrolist Project (C) 2026
 * Licensed under GPL-3.0 | See git history for contributors
 */

package com.metrolist.music.lyrics

import android.content.Context
import com.metrolist.innertube.YouTube
import com.metrolist.innertube.models.WatchEndpoint

object YouTubeMusicLyricsProvider : LyricsProvider {
    override val name = "YouTube Music"

    override fun isEnabled(context: Context): Boolean = true

    override suspend fun getLyrics(
        context: Context,
        id: String,
        title: String,
