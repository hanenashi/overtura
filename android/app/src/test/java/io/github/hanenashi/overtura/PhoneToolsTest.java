package io.github.hanenashi.overtura;

import org.junit.Test;
import static org.junit.Assert.*;

public class PhoneToolsTest {
    @Test public void reportsAvailableAndMissingTools() {
        PhoneTools result = PhoneTools.parse(0, "ssh ok\ntimeout missing\nnano ok\n");
        assertTrue(result.ssh);
        assertFalse(result.timeout);
        assertTrue(result.nano);
    }

    @Test public void rejectsFailedOrUnexpectedOutput() {
        for (String output : new String[]{"ssh ok\ntimeout ok\n", "ssh ok\nssh ok\nnano ok\n",
                "ssh ok\ntimeout ok\nnano ok\nprivate-data\n"}) {
            assertThrows(IllegalArgumentException.class, () -> PhoneTools.parse(0, output));
        }
        assertThrows(IllegalArgumentException.class,
            () -> PhoneTools.parse(1, "ssh ok\ntimeout ok\nnano ok\n"));
    }
}
