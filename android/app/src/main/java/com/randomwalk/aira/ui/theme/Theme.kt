package com.randomwalk.aira.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AccentOrange = Color(0xFFFF6A3D)

private val LightColors = lightColorScheme(
    primary = AccentOrange,
    secondary = Color(0xFF111827),
    background = Color(0xFFFAFAF9),
    surface = Color.White,
)

private val DarkColors = darkColorScheme(
    primary = AccentOrange,
    secondary = Color(0xFFE5E7EB),
    background = Color(0xFF111111),
    surface = Color(0xFF1A1A1A),
)

@Composable
fun AiraTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
