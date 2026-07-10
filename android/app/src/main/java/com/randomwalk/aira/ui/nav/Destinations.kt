package com.randomwalk.aira.ui.nav

sealed class Destination(val route: String) {
    data object Dashboard : Destination("dashboard")
    data object Analytics : Destination("analytics")
    data object KnowledgeBase : Destination("knowledge_base")
    data object Config : Destination("config")
    data object LiveCall : Destination("live_call")

    data object CallDetail : Destination("call_detail/{sessionId}") {
        const val ARG_SESSION_ID = "sessionId"
        fun createRoute(sessionId: String) = "call_detail/$sessionId"
    }
}

data class BottomNavItem(val destination: Destination, val label: String)

val bottomNavItems = listOf(
    BottomNavItem(Destination.Analytics, "Analytics"),
    BottomNavItem(Destination.Dashboard, "Call logs"),
    BottomNavItem(Destination.KnowledgeBase, "Knowledge base"),
    BottomNavItem(Destination.Config, "Config"),
)
