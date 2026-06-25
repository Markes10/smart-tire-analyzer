package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.ui.screens.CameraScreen
import com.example.ui.screens.HistoryScreen
import com.example.ui.screens.HomeScreen
import com.example.ui.screens.LoginScreen
import com.example.ui.screens.ResultScreen
import com.example.ui.theme.MyApplicationTheme
import com.example.viewmodel.TireTwinViewModel

class MainActivity : ComponentActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    enableEdgeToEdge()
    setContent {
      val viewModel: TireTwinViewModel = viewModel()
      val isDarkTheme by viewModel.isDarkTheme.collectAsState()
      val isLoggedIn by viewModel.isLoggedIn.collectAsState()

      MyApplicationTheme(darkTheme = isDarkTheme, dynamicColor = false) {
        val navController = rememberNavController()

        NavHost(
          navController = navController,
          startDestination = if (isLoggedIn) "home" else "login",
          modifier = Modifier.fillMaxSize()
        ) {
          composable("login") {
            LoginScreen(
              viewModel = viewModel,
              onLoginSuccess = {
                navController.navigate("home") {
                  popUpTo("login") { inclusive = true }
                }
              }
            )
          }
          composable("home") {
            HomeScreen(
              viewModel = viewModel,
              onNavigateToCamera = { navController.navigate("camera") },
              onNavigateToHistory = { navController.navigate("history") },
              onNavigateToResults = { navController.navigate("result") }
            )
          }
          composable("camera") {
            CameraScreen(
              viewModel = viewModel,
              onNavigateBack = { navController.popBackStack() },
              onNavigateToResults = {
                // Return to home first then push result to keep backstack clean
                navController.navigate("result") {
                  popUpTo("home")
                }
              }
            )
          }
          composable("result") {
            ResultScreen(
              viewModel = viewModel,
              onNavigateBack = { navController.popBackStack() }
            )
          }
          composable("history") {
            HistoryScreen(
              viewModel = viewModel,
              onNavigateBack = { navController.popBackStack() },
              onNavigateToHome = {
                navController.navigate("home") {
                  popUpTo("home") { inclusive = true }
                }
              }
            )
          }
        }
      }
    }
  }
}
