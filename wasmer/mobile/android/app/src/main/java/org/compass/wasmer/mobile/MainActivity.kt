package org.compass.wasmer.mobile

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebViewAssetLoader
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

class MainActivity : AppCompatActivity() {
    private val latch = CountDownLatch(1)
    private val resultJson = AtomicReference<String?>(null)
    private lateinit var status: TextView

    fun awaitResult(timeoutMs: Long): String? {
        latch.await(timeoutMs, TimeUnit.MILLISECONDS)
        return resultJson.get()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        status = TextView(this).apply { text = "verifying digest…" }
        val web = WebView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(status, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ))
            addView(web, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            ))
        }
        setContentView(root)

        val expected = assets.open("EXPECTED_SHA256").bufferedReader().use { Digest.loadExpected(it.readText()) }
        val wasm = assets.open("compass_core_bg.wasm").use { it.readBytes() }
        val actual = Digest.sha256Hex(wasm)
        if (actual != expected) {
            val err = JSONObject()
                .put("ok", false)
                .put("error", "digest mismatch expected=$expected actual=$actual")
                .put("expected_sha256", expected)
                .put("actual_sha256", actual)
                .toString()
            finishWith(err)
            return
        }
        status.text = "digest match $actual — loading WebView"

        val assetLoader = WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        web.settings.javaScriptEnabled = true
        web.settings.allowFileAccess = false
        web.settings.allowContentAccess = false
        web.addJavascriptInterface(Bridge(), "CompassNative")
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView,
                request: WebResourceRequest
            ): WebResourceResponse? = assetLoader.shouldInterceptRequest(request.url)
        }
        web.loadUrl("https://appassets.androidplatform.net/assets/index.html")
    }

    private fun finishWith(json: String) {
        resultJson.set(json)
        latch.countDown()
        runOnUiThread {
            status.text = json
            status.contentDescription = json
        }
    }

    inner class Bridge {
        @JavascriptInterface
        fun report(json: String) {
            finishWith(json)
        }
    }
}
