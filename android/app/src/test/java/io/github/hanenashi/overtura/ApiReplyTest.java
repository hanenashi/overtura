package io.github.hanenashi.overtura;

import org.json.JSONObject;
import org.junit.Test;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import static org.junit.Assert.*;

public class ApiReplyTest {
    static String fixture(String name) throws Exception {
        try (InputStream stream = ApiReplyTest.class.getResourceAsStream("/" + name + ".json")) {
            assertNotNull(stream);
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private void fails(ApiReply.FailureKind kind, int exit, String text, String command) {
        ApiReply.Failure error = assertThrows(ApiReply.Failure.class, () -> ApiReply.parse(exit, text, command));
        assertEquals(kind, error.kind);
        assertNull(error.getCause());
        assertFalse(error.getMessage().contains("private-value"));
    }

    @Test public void readsProducerFixtures() throws Exception {
        ApiReply capabilities = ApiReply.parse(0, fixture("capabilities"), "capabilities");
        assertTrue(capabilities.supportedCommands.contains("session.list"));
        ApiReply healthy = ApiReply.parse(0, fixture("doctor-ok"), "doctor");
        assertTrue(healthy.ready);
        assertEquals(7, healthy.checks.size());
        ApiReply unhealthy = ApiReply.parse(1, fixture("doctor-failed"), "doctor");
        assertFalse(unhealthy.ready);
        assertTrue(unhealthy.hasData);
        assertEquals("doctor_failed", unhealthy.errorCode);
        ApiReply sessions = ApiReply.parse(0, fixture("sessions"), "session.list");
        assertEquals(2, sessions.sessions.size());
        assertEquals(1, sessions.sessions.get(0).attachedClients);
        assertFalse(sessions.sessions.get(1).attachable);
        assertEquals("odd\\tname\\n\"quoted\"", sessions.sessions.get(1).name);
        assertThrows(UnsupportedOperationException.class, () -> sessions.sessions.clear());
    }

    @Test public void emptyListAndFailedQueryAreDifferent() throws Exception {
        ApiReply empty = ApiReply.parse(0, fixture("sessions-empty"), "session.list");
        assertTrue(empty.ok && empty.hasData && empty.sessions.isEmpty());
        ApiReply error = ApiReply.parse(1, fixture("dependency-error"), "session.list");
        assertFalse(error.ok || error.hasData);
        assertEquals("dependency_missing", error.errorCode);
    }

    @Test public void distinguishesTransportAndVersionFailures() throws Exception {
        fails(ApiReply.FailureKind.CONNECTION, 255, "private-value", "doctor");
        for (int exit : new int[]{126, 127, 2})
            fails(ApiReply.FailureKind.UNSUPPORTED_CLI, exit, "", "doctor");
        JSONObject root = new JSONObject(fixture("doctor-ok"));
        root.put("schema_version", 2);
        fails(ApiReply.FailureKind.UNSUPPORTED_SCHEMA, 0, root.toString(), "doctor");
    }

    @Test public void rejectsTruncationBannersTrailingDataAndExcessSize() throws Exception {
        String valid = fixture("doctor-ok");
        for (String text : new String[]{"", "private-value", "banner\n" + valid, valid + valid,
                valid.substring(0, valid.length() / 2), "x".repeat(ApiReply.MAX_BYTES + 1),
                "{\"extra\":" + "[".repeat(40) + "0" + "]".repeat(40) + "}"})
            fails(ApiReply.FailureKind.MALFORMED, 0, text, "doctor");
    }

    @Test public void doesNotCoerceWrongTypesOrAcceptMissingFields() throws Exception {
        for (Object value : new Object[]{"1", 1.5, true, JSONObject.NULL}) {
            JSONObject root = new JSONObject(fixture("doctor-ok")).put("schema_version", value);
            fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "doctor");
        }
        JSONObject root = new JSONObject(fixture("doctor-ok")).put("ok", "true");
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "doctor");
        root = new JSONObject(fixture("doctor-ok"));
        root.remove("error");
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "doctor");
    }

    @Test public void rejectsMismatchedCommandExitAndHealth() throws Exception {
        fails(ApiReply.FailureKind.MALFORMED, 1, fixture("doctor-ok"), "doctor");
        fails(ApiReply.FailureKind.MALFORMED, 0, fixture("doctor-failed"), "doctor");
        fails(ApiReply.FailureKind.MALFORMED, 0, fixture("doctor-ok"), "session.list");
        JSONObject root = new JSONObject(fixture("doctor-ok"));
        root.getJSONObject("data").put("ready", false);
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "doctor");
        root = new JSONObject(fixture("doctor-ok"));
        root.getJSONObject("data").getJSONArray("checks").remove(0);
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "doctor");
    }

    @Test public void validatesSessionIdentityCountsAndAttachability() throws Exception {
        for (String field : new String[]{"id", "windows", "attached_clients", "attachable"}) {
            JSONObject root = new JSONObject(fixture("sessions"));
            root.getJSONObject("data").getJSONArray("sessions").getJSONObject(0).put(field, "private-value");
            fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "session.list");
        }
        JSONObject root = new JSONObject(fixture("sessions"));
        root.getJSONObject("data").getJSONArray("sessions").getJSONObject(1).put("attachable", true);
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "session.list");
        root = new JSONObject(fixture("sessions"));
        root.getJSONObject("data").getJSONArray("sessions").getJSONObject(1).put("id", "$0");
        fails(ApiReply.FailureKind.MALFORMED, 0, root.toString(), "session.list");
    }
}
