package com.randomwalk.aira.ui.nav

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.randomwalk.aira.ui.call.LiveCallScreen
import com.randomwalk.aira.ui.components.ComingSoonScreen
import com.randomwalk.aira.ui.dashboard.CallDetailScreen
import com.randomwalk.aira.ui.dashboard.DashboardScreen

private fun iconFor(destination: Destination) = when (destination) {
    Destination.Analytics -> Icons.Filled.BarChart
    Destination.Dashboard -> Icons.Filled.Phone
    Destination.KnowledgeBase -> Icons.Filled.Book
    Destination.Config -> Icons.Filled.Settings
    else -> Icons.Filled.Phone
}

@Composable
fun AiraApp() {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            val backStackEntry by navController.currentBackStackEntryAsState()
            val currentDestination = backStackEntry?.destination
            NavigationBar {
                bottomNavItems.forEach { item ->
                    val selected = currentDestination?.hierarchy?.any { it.route == item.destination.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(item.destination.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(iconFor(item.destination), contentDescription = item.label) },
                        label = { Text(item.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Destination.Dashboard.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(Destination.Dashboard.route) {
                DashboardScreen(
                    onOpenCall = { sessionId ->
                        navController.navigate(Destination.CallDetail.createRoute(sessionId))
                    },
                    onStartTestCall = { navController.navigate(Destination.LiveCall.route) },
                )
            }
            composable(Destination.Analytics.route) { ComingSoonScreen("Analytics") }
            composable(Destination.KnowledgeBase.route) { ComingSoonScreen("Knowledge base") }
            composable(Destination.Config.route) { ComingSoonScreen("Config") }
            composable(Destination.LiveCall.route) {
                LiveCallScreen(onBack = { navController.popBackStack() })
            }
            composable(Destination.CallDetail.route) {
                CallDetailScreen(onBack = { navController.popBackStack() })
            }
        }
    }
}
