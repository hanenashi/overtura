package io.github.hanenashi.overtura;

import org.junit.Test;
import static org.junit.Assert.*;
import static io.github.hanenashi.overtura.ApiReplyTest.fixture;

public class QueryStateTest {
    @Test public void ignoresSupersededAndRepeatedCallbacks() throws Exception {
        QueryState state = new QueryState();
        long first = state.begin("my-node", "session.list", 0);
        long second = state.begin("my-node", "session.list", 1);
        assertFalse(state.complete(first, 0, fixture("sessions"), 2));
        assertTrue(state.complete(second, 0, fixture("sessions-empty"), 3));
        assertFalse(state.complete(second, 0, fixture("sessions"), 4));
        assertTrue(state.snapshot().sessions.isEmpty());
        assertEquals(QueryState.Status.READY, state.status());
    }

    @Test public void clearsSnapshotWhenHostOrOperationChanges() throws Exception {
        QueryState state = new QueryState();
        long request = state.begin("first-node", "session.list", 0);
        state.complete(request, 0, fixture("sessions"), 1);
        request = state.begin("second-node", "session.list", 2);
        assertNull(state.snapshot());
        state.complete(request, 0, fixture("sessions-empty"), 3);
        state.begin("second-node", "doctor", 4);
        assertNull(state.snapshot());
    }

    @Test public void timeoutRejectsLateReply() throws Exception {
        QueryState state = new QueryState();
        long request = state.begin("my-node", "doctor", 100);
        state.expire(100 + QueryState.TIMEOUT_MS - 1);
        assertEquals(QueryState.Status.LOADING, state.status());
        assertFalse(state.complete(request, 0, fixture("doctor-ok"), 100 + QueryState.TIMEOUT_MS));
        assertEquals(ApiReply.FailureKind.TIMEOUT, state.failure().kind);
        assertNull(state.snapshot());
    }

    @Test public void failedRefreshRetainsOnlyStaleSnapshot() throws Exception {
        QueryState state = new QueryState();
        long request = state.begin("my-node", "session.list", 0);
        state.complete(request, 0, fixture("sessions"), 1);
        assertFalse(state.isStale(2));
        assertTrue(state.isStale(1 + QueryState.FRESH_MS));
        request = state.begin("my-node", "session.list", 3);
        assertTrue(state.isStale(3));
        state.complete(request, 1, fixture("dependency-error"), 4);
        assertEquals(QueryState.Status.ERROR, state.status());
        assertEquals("dependency_missing", state.remoteError());
        assertEquals(2, state.snapshot().sessions.size());
        assertTrue(state.isStale(4));
        request = state.begin("my-node", "session.list", 5);
        state.complete(request, 0, fixture("sessions-empty"), 6);
        assertNull(state.remoteError());
        assertFalse(state.isStale(6));
        assertTrue(state.snapshot().sessions.isEmpty());
    }

    @Test public void failedDoctorIsFreshActionableData() throws Exception {
        QueryState state = new QueryState();
        long request = state.begin("my-node", "doctor", 0);
        state.complete(request, 1, fixture("doctor-failed"), 1);
        assertEquals(QueryState.Status.NEEDS_ATTENTION, state.status());
        assertFalse(state.snapshot().ready);
        assertFalse(state.isStale(2));
    }

    @Test public void cancellationAndConnectionFailureCannotRefreshData() throws Exception {
        QueryState state = new QueryState();
        long request = state.begin("my-node", "doctor", 0);
        state.complete(request, 0, fixture("doctor-ok"), 1);
        request = state.begin("my-node", "doctor", 2);
        state.complete(request, 255, "private-value", 3);
        assertEquals(ApiReply.FailureKind.CONNECTION, state.failure().kind);
        assertTrue(state.isStale(3));
        request = state.begin("my-node", "doctor", 4);
        state.cancel();
        assertFalse(state.complete(request, 0, fixture("doctor-ok"), 5));
        assertEquals(QueryState.Status.IDLE, state.status());
        assertTrue(state.isStale(5));
    }
}
