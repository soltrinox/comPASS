package org.compass.wasmer.mobile

import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.atomic.AtomicReference

@RunWith(AndroidJUnit4::class)
class DecideParityTest {
    @Test
    fun fixtureMinAndMissingSnapshot() {
        val scenario = ActivityScenario.launch(MainActivity::class.java)
        val activityRef = AtomicReference<MainActivity>()
        scenario.onActivity { activityRef.set(it) }
        val json = activityRef.get().awaitResult(90_000L)
        assertNotNull(
            "WebView did not report compassResult (emulator/device required; this is not a host-side fake)",
            json
        )
        val obj = JSONObject(json!!)
        assertTrue(obj.optString("error"), obj.getBoolean("ok"))
        assertEquals(
            "urn:mg:model:cheap",
            obj.getJSONObject("fixture_min").getString("selected_model_version_id")
        )
        assertEquals(
            "snapshot_missing",
            obj.getJSONObject("missing").getString("default_reason")
        )
    }
}
