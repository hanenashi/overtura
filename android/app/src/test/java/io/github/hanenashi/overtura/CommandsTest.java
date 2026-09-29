package io.github.hanenashi.overtura;

import org.junit.Test;
import static org.junit.Assert.*;
import java.nio.charset.StandardCharsets;

public class CommandsTest {
    @Test public void rejectsShellSyntaxInHostAndSession() {
        for (String input : new String[]{"", "-oProxyCommand=x", "node;touch x", "$(id)", "a\nb", "user@host", "'quote", "a/b"}) {
            assertThrows(IllegalArgumentException.class, () -> Commands.remote(input, "list", "work"));
        }
        for (String input : new String[]{"", "a:b", "a.b", "../work", "name;id", "$(id)", "'", "a".repeat(65)}) {
            assertThrows(IllegalArgumentException.class, () -> Commands.remote("my-node", "create", input));
        }
    }

    @Test public void shellReceivesExactlyOneRemoteCommand() throws Exception {
        String command = Commands.remote("my-node", "attach", "work_2");
        Process process = new ProcessBuilder("/bin/sh", "-c", "ssh() { printf '%s\\n' \"$@\"; }; " + command).start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertEquals(0, process.waitFor());
        assertEquals("-t\n--\nmy-node\nexec \"$HOME/.local/bin/overtura\" session attach 'work_2'\n", output);
    }

    @Test public void supportsNamesAndReadOnlyActions() {
        assertEquals("my-node", Commands.alias(" my-node "));
        assertEquals("w".repeat(64), Commands.session("w".repeat(64)));
        assertTrue(Commands.remote("my.node", "doctor", "").contains("doctor"));
        assertTrue(Commands.remote("my-node", "list", "").contains("session list"));
        assertThrows(IllegalArgumentException.class, () -> Commands.remote("my-node", "delete", "work"));
    }
    @Test public void backgroundQueriesAreReadOnlyAndKeepShellBoundaries() throws Exception {
        for (String operation : new String[]{"capabilities", "doctor", "session.list"}) {
            String command = Commands.readOnlyQuery("my-node", operation);
            Process process = new ProcessBuilder("/bin/sh", "-c", "ssh() { printf '%s\\n' \"$@\"; }; " + command).start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            assertEquals(0, process.waitFor());
            assertTrue(output.startsWith("-T\n-o\nBatchMode=yes\n"));
            assertTrue(output.endsWith("--\nmy-node\nexec \"$HOME/.local/bin/overtura\" --json " + operation.replace('.', ' ') + "\n"));
        }
        assertThrows(IllegalArgumentException.class, () -> Commands.readOnlyQuery("my-node", "session.create"));
        assertThrows(IllegalArgumentException.class, () -> Commands.readOnlyQuery("my-node;id", "doctor"));
    }
}
