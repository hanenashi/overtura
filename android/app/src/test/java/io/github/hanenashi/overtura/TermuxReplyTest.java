package io.github.hanenashi.overtura;

import org.junit.Test;
import java.nio.charset.StandardCharsets;
import static org.junit.Assert.*;
import static io.github.hanenashi.overtura.ApiReplyTest.fixture;

public class TermuxReplyTest {
    @Test public void acceptsCompleteDoctorAndListResponses() throws Exception {
        for (String name : new String[]{"doctor-ok", "doctor-failed", "sessions-empty"}) {
            String stdout = fixture(name);
            TermuxReply reply = TermuxReply.from(true, -1, true,
                name.equals("doctor-failed") ? 1 : 0, stdout,
                String.valueOf(stdout.getBytes(StandardCharsets.UTF_8).length));
            assertNull(reply.failure);
            QueryState state = new QueryState();
            String operation = name.startsWith("sessions") ? "session.list" : "doctor";
            long token = state.begin("my-node", operation, 0);
            assertTrue(state.complete(token, reply.exitCode, reply.stdout, 1));
            assertNotNull(state.snapshot());
        }
    }

    @Test public void rejectsMissingCorruptAndTruncatedResults() {
        assertEquals(ApiReply.FailureKind.MALFORMED,
            TermuxReply.from(false, 0, true, 0, "{}", 2).failure);
        assertEquals(ApiReply.FailureKind.MALFORMED,
            TermuxReply.from(true, -1, false, 0, "{}", 2).failure);
        assertEquals(ApiReply.FailureKind.TERMUX_SETUP,
            TermuxReply.from(true, 1, true, 0, "private-value", 13).failure);
        assertEquals(ApiReply.FailureKind.MALFORMED,
            TermuxReply.from(true, -1, true, 0, "{}", "bad").failure);
        assertEquals(ApiReply.FailureKind.MALFORMED,
            TermuxReply.from(true, -1, true, 0, "{}", 100000).failure);
        assertEquals(ApiReply.FailureKind.MALFORMED,
            TermuxReply.from(true, -1, true, 0, "x".repeat(ApiReply.MAX_BYTES + 1), 0).failure);
    }

    @Test public void timeoutAndLateResultCannotBecomeFresh() throws Exception {
        String stdout = fixture("doctor-ok");
        QueryState state = new QueryState();
        long token = state.begin("my-node", "doctor", 0);
        assertFalse(state.complete(token, 0, stdout, QueryState.TIMEOUT_MS));
        assertEquals(ApiReply.FailureKind.TIMEOUT, state.failure().kind);
        token = state.begin("my-node", "doctor", QueryState.TIMEOUT_MS + 1);
        assertTrue(state.complete(token, 124, "", QueryState.TIMEOUT_MS + 2));
        assertEquals(ApiReply.FailureKind.TIMEOUT, state.failure().kind);
    }
}
