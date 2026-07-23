package com.aira.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.aira.mobile.data.source.local.CallDatabaseHelper
import com.aira.mobile.domain.repository.AgentRepository
import com.aira.mobile.presentation.home.HomeScreen
import com.aira.mobile.presentation.permissions.PermissionsScreen
import com.aira.mobile.presentation.config.AgentConfigScreen
import com.aira.mobile.presentation.analytics.AnalyticsScreen
import com.aira.mobile.presentation.history.CallHistoryScreen
import com.aira.mobile.presentation.fallback.FallbackSettingsScreen
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

enum class AppScreen {
    Home,
    Permissions,
    Config,
    Analytics,
    History,
    Fallback
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var agentRepository: AgentRepository

    @Inject
    lateinit var dbHelper: CallDatabaseHelper

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var currentScreen by remember { mutableStateOf(AppScreen.Home) }

            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    when (currentScreen) {
                        AppScreen.Home -> {
                            HomeScreen(
                                agentRepository = agentRepository,
                                onNavigateToPermissions = {
                                    currentScreen = AppScreen.Permissions
                                },
                                onNavigateToConfig = {
                                    currentScreen = AppScreen.Config
                                },
                                onNavigateToAnalytics = {
                                    currentScreen = AppScreen.Analytics
                                },
                                onNavigateToHistory = {
                                    currentScreen = AppScreen.History
                                },
                                onNavigateToFallback = {
                                    currentScreen = AppScreen.Fallback
                                }
                            )
                        }
                        AppScreen.Permissions -> {
                            PermissionsScreen(
                                onNavigateBack = {
                                    currentScreen = AppScreen.Home
                                }
                            )
                        }
                        AppScreen.Config -> {
                            AgentConfigScreen(
                                agentRepository = agentRepository,
                                onNavigateBack = {
                                    currentScreen = AppScreen.Home
                                }
                            )
                        }
                        AppScreen.Analytics -> {
                            AnalyticsScreen(
                                agentRepository = agentRepository,
                                onNavigateBack = {
                                    currentScreen = AppScreen.Home
                                }
                            )
                        }
                        AppScreen.History -> {
                            CallHistoryScreen(
                                dbHelper = dbHelper,
                                agentRepository = agentRepository,
                                onNavigateBack = {
                                    currentScreen = AppScreen.Home
                                }
                            )
                        }
                        AppScreen.Fallback -> {
                            FallbackSettingsScreen(
                                onNavigateBack = {
                                    currentScreen = AppScreen.Home
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}
