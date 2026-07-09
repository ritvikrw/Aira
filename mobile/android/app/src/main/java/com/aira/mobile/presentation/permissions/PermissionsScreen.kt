package com.aira.mobile.presentation.permissions

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.telecom.TelecomManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.aira.mobile.service.TelecomHelper

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PermissionsScreen(
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val telecomHelper = remember { TelecomHelper(context) }

    // List of required permissions
    val requiredPermissions = remember {
        mutableListOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ANSWER_PHONE_CALLS,
            Manifest.permission.MANAGE_OWN_CALLS,
            Manifest.permission.READ_PHONE_STATE
        ).apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toList()
    }

    // Dynamic state trackers
    var permissionsState by remember {
        mutableStateOf(
            requiredPermissions.associateWith { permission ->
                ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
            }
        )
    }

    var isDefaultDialer by remember { mutableStateOf(telecomHelper.isDefaultDialer()) }
    var isPhoneAccountRegistered by remember { mutableStateOf(telecomHelper.isPhoneAccountRegistered()) }
    
    val powerManager = remember { context.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager }
    var isIgnoringBatteryOptimizations by remember {
        mutableStateOf(powerManager.isIgnoringBatteryOptimizations(context.packageName))
    }

    // Launchers
    val permissionsLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        permissionsState = requiredPermissions.associateWith { permission ->
            result[permission] ?: (ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED)
        }
    }

    val roleLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { _ ->
        isDefaultDialer = telecomHelper.isDefaultDialer()
    }

    // Refresh status helper
    fun refreshAllStates() {
        permissionsState = requiredPermissions.associateWith { permission ->
            ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        }
        isDefaultDialer = telecomHelper.isDefaultDialer()
        isPhoneAccountRegistered = telecomHelper.isPhoneAccountRegistered()
        isIgnoringBatteryOptimizations = powerManager.isIgnoringBatteryOptimizations(context.packageName)
    }

    // Refresh on screen launch
    LaunchedEffect(Unit) {
        refreshAllStates()
    }

    val allPermissionsGranted = permissionsState.values.all { it }
    val setupComplete = allPermissionsGranted && isDefaultDialer && isPhoneAccountRegistered && isIgnoringBatteryOptimizations

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF1A1B2F),
                        Color(0xFF12131C)
                    )
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onNavigateBack,
                    colors = IconButtonDefaults.iconButtonColors(containerColor = Color(0xFF2C2D4A))
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = Color.White
                    )
                }
                
                Spacer(modifier = Modifier.width(16.dp))
                
                Column {
                    Text(
                        text = "Setup Checklist",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Configure device permissions & roles",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            // Permissions Checklist
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF23243C)),
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(vertical = 24.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(20.dp),
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Requirements Checklist",
                        color = Color(0xFF8A9AFA),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))

                    Column(
                        modifier = Modifier.weight(1f),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // 1. Android Permissions Group
                        ChecklistItem(
                            title = "System Audio & Phone Permissions",
                            subtitle = "Record audio, answer calls, phone state monitoring",
                            isDone = allPermissionsGranted,
                            onAction = {
                                permissionsLauncher.launch(requiredPermissions.toTypedArray())
                            },
                            actionLabel = "Grant"
                        )

                        // 2. Dialer Role Selection
                        ChecklistItem(
                            title = "Default Phone App Role",
                            subtitle = "Required to intercept and auto-answer SIM calls",
                            isDone = isDefaultDialer,
                            onAction = {
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                                    val roleManager = context.getSystemService(Context.ROLE_SERVICE) as RoleManager
                                    val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_DIALER)
                                    roleLauncher.launch(intent)
                                } else {
                                    val intent = Intent(TelecomManager.ACTION_CHANGE_DEFAULT_DIALER).apply {
                                        putExtra(TelecomManager.EXTRA_CHANGE_DEFAULT_DIALER_PACKAGE_NAME, context.packageName)
                                    }
                                    roleLauncher.launch(intent)
                                }
                            },
                            actionLabel = "Select"
                        )

                        // 3. PhoneAccount Registration
                        ChecklistItem(
                            title = "Register Call Account",
                            subtitle = "Integrates with system Telecom framework",
                            isDone = isPhoneAccountRegistered,
                            onAction = {
                                telecomHelper.registerPhoneAccount()
                                refreshAllStates()
                            },
                            actionLabel = "Register"
                        )

                        // 4. Battery Optimization Whitelist
                        ChecklistItem(
                            title = "Ignore Battery Optimizations",
                            subtitle = "Required to run receptionist when locked or idle",
                            isDone = isIgnoringBatteryOptimizations,
                            onAction = {
                                try {
                                    val intent = Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                                        data = android.net.Uri.parse("package:${context.packageName}")
                                    }
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    android.util.Log.e("PermissionsScreen", "Failed to launch battery settings", e)
                                }
                            },
                            actionLabel = "Whitelist"
                        )
                    }

                    // Setup status message
                    if (setupComplete) {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFF1B3B2B),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.CheckCircle,
                                    contentDescription = null,
                                    tint = Color(0xFF4CAF50)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Text(
                                    text = "All integrations are active! The AI agent is fully functional.",
                                    color = Color.LightGray,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    } else {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFF3F3415),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = null,
                                    tint = Color(0xFFFFC107)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Text(
                                    text = "Please complete all setup steps to enable automated receptionist services.",
                                    color = Color.LightGray,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                }
            }

            // Bottom action: Back to Home
            Button(
                onClick = onNavigateBack,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (setupComplete) Color(0xFF4CAF50) else Color(0xFF5A6BFA)
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Text(
                    text = if (setupComplete) "Go to Home Screen" else "Proceed anyway",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun ChecklistItem(
    title: String,
    subtitle: String,
    isDone: Boolean,
    onAction: () -> Unit,
    actionLabel: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF1E1F35), RoundedCornerShape(14.dp))
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = subtitle,
                color = Color.Gray,
                fontSize = 11.sp
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        if (isDone) {
            Icon(
                imageVector = Icons.Default.CheckCircle,
                contentDescription = "Completed",
                tint = Color(0xFF4CAF50),
                modifier = Modifier.size(24.dp)
            )
        } else {
            Button(
                onClick = onAction,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2C2D4A)),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.height(34.dp)
            ) {
                Text(
                    text = actionLabel,
                    color = Color.White,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
