package org.compass.wasmer.mobile

import java.security.MessageDigest

object Digest {
    fun sha256Hex(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
        return digest.joinToString("") { b -> "%02x".format(b) }
    }

    fun loadExpected(text: String): String =
        text.trim().lowercase()
}
