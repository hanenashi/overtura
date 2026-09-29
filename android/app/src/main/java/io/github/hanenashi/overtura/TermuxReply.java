package io.github.hanenashi.overtura;

import java.nio.charset.StandardCharsets;

/** Validates Termux's bounded background result without retaining stderr. */
final class TermuxReply {
    final int exitCode;
    final String stdout;
    final ApiReply.FailureKind failure;

    private TermuxReply(int exitCode, String stdout, ApiReply.FailureKind failure) {
        this.exitCode = exitCode;
        this.stdout = stdout;
        this.failure = failure;
    }

    static TermuxReply from(boolean hasError, int termuxError, boolean hasExit,
                            int exitCode, String stdout, Object originalLength) {
        if (!hasError || !hasExit) return new TermuxReply(0, null, ApiReply.FailureKind.MALFORMED);
        if (termuxError != -1) return new TermuxReply(0, null, ApiReply.FailureKind.TERMUX_SETUP);
        long original;
        try {
            original = originalLength instanceof Number ? ((Number)originalLength).longValue()
                : originalLength instanceof String ? Long.parseLong((String)originalLength) : -1;
        } catch (NumberFormatException error) {
            return new TermuxReply(0, null, ApiReply.FailureKind.MALFORMED);
        }
        if (stdout == null || original < 0) return new TermuxReply(0, null, ApiReply.FailureKind.MALFORMED);
        int bytes = stdout.getBytes(StandardCharsets.UTF_8).length;
        if (bytes > ApiReply.MAX_BYTES || original > bytes)
            return new TermuxReply(0, null, ApiReply.FailureKind.MALFORMED);
        return new TermuxReply(exitCode, stdout, null);
    }
}
