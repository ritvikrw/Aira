package com.randomwalk.aira.di

import com.randomwalk.aira.data.network.AiraApiService
import com.randomwalk.aira.data.prefs.BackendSettings
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import okhttp3.MediaType.Companion.toMediaType
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import javax.inject.Singleton

/**
 * Rewrites the scheme/host/port of every request to whatever BackendSettings currently
 * holds, so the app's target backend can be changed at runtime (e.g. emulator vs LAN IP)
 * without rebuilding Retrofit. Retrofit itself is configured with a placeholder base URL
 * and real relative paths (e.g. "calls/") — only scheme/host/port get swapped here.
 */
private class DynamicBaseUrlInterceptor(private val backendSettings: BackendSettings) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val configured = runBlocking { backendSettings.baseUrl.first() }.toHttpUrl()
        val original = chain.request()
        val newUrl = original.url.newBuilder()
            .scheme(configured.scheme)
            .host(configured.host)
            .port(configured.port)
            .build()
        return chain.proceed(original.newBuilder().url(newUrl).build())
    }
}

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private const val PLACEHOLDER_BASE_URL = "http://placeholder.local/"

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(backendSettings: BackendSettings): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        return OkHttpClient.Builder()
            .addInterceptor(DynamicBaseUrlInterceptor(backendSettings))
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(PLACEHOLDER_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    fun provideAiraApiService(retrofit: Retrofit): AiraApiService =
        retrofit.create(AiraApiService::class.java)
}
