package com.campro.v5.pipeline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.nio.file.Files

class BridgeWorkingDirectoryTest {
    @JvmField
    @Rule
    val temp = TemporaryFolder()

    @Test
    fun `legacy mode uses user dir as cwd`() {
        val userDir = temp.root.toPath()
        val wd = BridgeInvocation.resolveWorkingDirectoryInternal(
            legacyCli = true,
            resolvedScriptPath = "../scripts/kotlin_bridge_cli.py",
            larrickMultiRootEnv = null,
            userDir = userDir,
        )
        assertEquals(temp.root, wd)
    }

    @Test
    fun `LARRICK_MULTI_ROOT wins when directory exists`() {
        val repo = temp.newFolder("larrick_multi").toPath()
        val userDir = temp.newFolder("cwd").toPath()
        val wd = BridgeInvocation.resolveWorkingDirectoryInternal(
            legacyCli = false,
            resolvedScriptPath = "/nonexistent/scripts/larrick_gui_bridge.py",
            larrickMultiRootEnv = repo.toString(),
            userDir = userDir,
        )
        assertEquals(repo.toFile(), wd)
    }

    @Test
    fun `derives repo root from absolute bridge script path`() {
        val repo = temp.newFolder("larrick_multi").toPath()
        val scripts = repo.resolve("scripts")
        Files.createDirectories(scripts)
        val bridge = scripts.resolve("larrick_gui_bridge.py")
        Files.createFile(bridge)
        val userDir = temp.newFolder("other").toPath()

        val wd = BridgeInvocation.resolveWorkingDirectoryInternal(
            legacyCli = false,
            resolvedScriptPath = bridge.toString(),
            larrickMultiRootEnv = null,
            userDir = userDir,
        )
        assertEquals(repo.toFile(), wd)
    }

    @Test
    fun `derives repo root from relative bridge script path`() {
        val repo = temp.newFolder("larrick_multi").toPath()
        val scripts = repo.resolve("scripts")
        Files.createDirectories(scripts)
        val bridge = scripts.resolve("larrick_gui_bridge.py")
        Files.createFile(bridge)
        val userDir = repo.resolve("GUI/desktop")
        Files.createDirectories(userDir)

        val wd = BridgeInvocation.resolveWorkingDirectoryInternal(
            legacyCli = false,
            resolvedScriptPath = "../../scripts/larrick_gui_bridge.py",
            larrickMultiRootEnv = null,
            userDir = userDir,
        )
        assertEquals(repo.toFile(), wd)
    }

    @Test
    fun `invalid env falls back to user dir when script not resolved`() {
        val userDir = temp.newFolder("cwd").toPath()
        val wd = BridgeInvocation.resolveWorkingDirectoryInternal(
            legacyCli = false,
            resolvedScriptPath = "/no/such/larrick_gui_bridge.py",
            larrickMultiRootEnv = "/no/such/root",
            userDir = userDir,
        )
        assertEquals(userDir.toFile(), wd)
    }

    @Test
    fun `bridgeOutputIndicatesSuccess matches success status`() {
        assertTrue(BridgeInvocation.bridgeOutputIndicatesSuccess(mapOf("status" to "success")))
        assertFalse(BridgeInvocation.bridgeOutputIndicatesSuccess(mapOf("status" to "failed")))
        assertFalse(BridgeInvocation.bridgeOutputIndicatesSuccess(emptyMap()))
    }
}
