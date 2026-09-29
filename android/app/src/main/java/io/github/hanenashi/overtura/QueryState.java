package io.github.hanenashi.overtura;

/** One read-only view's request lifecycle. Caller supplies monotonic milliseconds. */
public final class QueryState {
    public static final long TIMEOUT_MS = 20000;
    public static final long FRESH_MS = 30000;
    public enum Status { IDLE, LOADING, READY, NEEDS_ATTENTION, ERROR }
    private long generation, active = -1, startedAt, receivedAt;
    private String host, operation;
    private ApiReply snapshot;
    private boolean invalidated;
    private Status status = Status.IDLE;
    private ApiReply.Failure failure;
    private String remoteError;

    public long begin(String newHost, String newOperation, long now) {
        String normalizedHost = Commands.alias(newHost);
        Commands.readOnlyQuery(normalizedHost, newOperation);
        if (!normalizedHost.equals(host) || !newOperation.equals(operation)) {
            snapshot = null;
        }
        host = normalizedHost;
        operation = newOperation;
        startedAt = now;
        active = ++generation;
        invalidated = true;
        status = Status.LOADING;
        failure = null;
        remoteError = null;
        return active;
    }

    public boolean complete(long request, int exitCode, String stdout, long now) {
        expire(now);
        if (request != active || status != Status.LOADING) return false;
        active = -1;
        try {
            ApiReply reply = ApiReply.parse(exitCode, stdout, operation);
            if (reply.hasData) {
                snapshot = reply;
                receivedAt = now;
                invalidated = false;
                status = reply.ok ? Status.READY : Status.NEEDS_ATTENTION;
            } else {
                status = Status.ERROR;
                // A structured remote error is useful, but cannot refresh old data.
                remoteError = reply.errorCode;
            }
        } catch (ApiReply.Failure error) {
            failure = error;
            status = Status.ERROR;
        }
        return true;
    }

    public String remoteError() { return remoteError; }

    public void expire(long now) {
        if (status == Status.LOADING && now - startedAt >= TIMEOUT_MS) {
            active = -1;
            failure = new ApiReply.Failure(ApiReply.FailureKind.TIMEOUT);
            status = Status.ERROR;
        }
    }

    public void cancel() {
        active = -1;
        invalidated = true;
        status = Status.IDLE;
        failure = null;
        remoteError = null;
    }

    public boolean isStale(long now) {
        return snapshot != null && (invalidated || now - receivedAt >= FRESH_MS);
    }

    public Status status() { return status; }
    public ApiReply snapshot() { return snapshot; }
    public ApiReply.Failure failure() { return failure; }
}
