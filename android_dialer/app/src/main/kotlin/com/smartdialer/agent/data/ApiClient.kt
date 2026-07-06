package com.smartdialer.agent.data

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private var baseUrl: String = "http://10.0.2.2:5001/"  // localhost from emulator
    private var token: String = ""

    fun configure(url: String, authToken: String) {
        baseUrl = if (url.endsWith("/")) url else "$url/"
        token = authToken
        _service = null  // force rebuild
    }

    fun setToken(authToken: String) {
        token = authToken
        _service = null
    }

    private var _service: ApiService? = null

    val service: ApiService
        get() {
            if (_service == null) {
                val logging = HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }
                val authInterceptor = Interceptor { chain ->
                    val req = if (token.isNotEmpty()) {
                        chain.request().newBuilder()
                            .addHeader("Authorization", "Bearer $token")
                            .build()
                    } else chain.request()
                    chain.proceed(req)
                }
                val client = OkHttpClient.Builder()
                    .addInterceptor(authInterceptor)
                    .addInterceptor(logging)
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(30, TimeUnit.SECONDS)
                    .build()

                _service = Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(ApiService::class.java)
            }
            return _service!!
        }

    // Raw OkHttpClient for WebSocket (no base URL needed)
    val wsClient: okhttp3.OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.SECONDS)  // no timeout for WS
            .build()
    }
}
