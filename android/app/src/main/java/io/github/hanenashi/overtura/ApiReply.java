package io.github.hanenashi.overtura;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Validates the v1 wire format without retaining raw stdout or stderr. */
public final class ApiReply {
    public static final int MAX_BYTES = 262144;
    public enum FailureKind { CONNECTION, UNSUPPORTED_CLI, UNSUPPORTED_SCHEMA, MALFORMED, TIMEOUT, TERMUX_SETUP }
    public static final class Failure extends Exception {
        public final FailureKind kind;
        public Failure(FailureKind kind) {
            super(switch (kind) {
                case CONNECTION -> "SSH could not complete the request. Check the host connection in Termux.";
                case UNSUPPORTED_CLI -> "Update the host CLI or check its installation in Termux.";
                case UNSUPPORTED_SCHEMA -> "The host uses an unsupported API version.";
                case MALFORMED -> "The host reply could not be read. Check CLI compatibility and shell startup output.";
                case TIMEOUT -> "The request timed out. Previous results may be out of date.";
                case TERMUX_SETUP -> "Termux could not run this query. Check its installation, Run commands permission, and allow-external-apps setting.";
            });
            this.kind = kind;
        }
    }

    public static final class Check {
        public final String id, status, message;
        private Check(String id, String status, String message) {
            this.id = id; this.status = status; this.message = message;
        }
    }

    public static final class Session {
        public final String id, name;
        public final int windows, attachedClients;
        public final boolean attachable;
        private Session(String id, String name, int windows, int attachedClients, boolean attachable) {
            this.id = id; this.name = name; this.windows = windows;
            this.attachedClients = attachedClients; this.attachable = attachable;
        }
    }

    public final String cliVersion, command, errorCode, errorMessage;
    public final boolean ok, hasData, ready;
    public final List<Check> checks;
    public final List<Session> sessions;
    public final List<String> supportedCommands;

    private ApiReply(JSONObject root, String expected) throws JSONException, Failure {
        if (integer(root, "schema_version", 1) != 1) throw new Failure(FailureKind.UNSUPPORTED_SCHEMA);
        cliVersion = string(root, "cli_version", 64);
        command = string(root, "command", 64);
        require(command.equals(expected));
        ok = bool(root, "ok");
        require(root.has("error") && root.has("data"));
        if (ok) {
            require(root.isNull("error"));
            errorCode = null; errorMessage = null;
        } else {
            JSONObject error = root.getJSONObject("error");
            errorCode = string(error, "code", 64);
            require(errorCode.matches("[a-z][a-z0-9_]{0,63}"));
            errorMessage = string(error, "message", 1024);
        }
        hasData = !root.isNull("data");
        require(!ok || hasData);
        List<Check> parsedChecks = new ArrayList<>();
        List<Session> parsedSessions = new ArrayList<>();
        List<String> commands = new ArrayList<>();
        boolean parsedReady = false;
        if (hasData) {
            JSONObject data = root.getJSONObject("data");
            switch (command) {
                case "doctor":
                    parsedReady = bool(data, "ready");
                    require(parsedReady == ok);
                    JSONArray rows = data.getJSONArray("checks");
                    Set<String> checkIds = new HashSet<>();
                    boolean failed = false;
                    for (int i = 0; i < rows.length(); i++) {
                        JSONObject row = rows.getJSONObject(i);
                        String id = string(row, "id", 128);
                        String status = string(row, "status", 16);
                        require(checkIds.add(id) && Set.of("ok", "warn", "fail", "info").contains(status));
                        failed |= status.equals("fail");
                        parsedChecks.add(new Check(id, status, string(row, "message", 1024)));
                    }
                    require(checkIds.containsAll(Set.of("python", "tmux", "ssh", "config", "durability")));
                    require(!parsedReady || checkIds.contains("workspace"));
                    require(failed != parsedReady);
                    break;
                case "session.list":
                    require(ok);
                    JSONArray list = data.getJSONArray("sessions");
                    Set<String> ids = new HashSet<>();
                    for (int i = 0; i < list.length(); i++) {
                        JSONObject row = list.getJSONObject(i);
                        String id = string(row, "id", 64);
                        String name = string(row, "name", 4096);
                        boolean attachable = bool(row, "attachable");
                        require(id.matches("\\$[0-9]+") && ids.add(id));
                        require(!attachable || name.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"));
                        parsedSessions.add(new Session(id, name, integer(row, "windows", 1),
                            integer(row, "attached_clients", 0), attachable));
                    }
                    break;
                case "capabilities":
                    require(ok);
                    require(integer(data, "config_version", 1) == 1);
                    JSONArray versions = data.getJSONArray("schema_versions");
                    boolean compatible = false;
                    for (int i = 0; i < versions.length(); i++) {
                        Object version = versions.get(i);
                        require(version instanceof Integer || version instanceof Long);
                        compatible |= ((Number)version).longValue() == 1;
                    }
                    require(compatible && bool(data, "session_create_requires_detach"));
                    JSONArray supported = data.getJSONArray("json_commands");
                    for (int i = 0; i < supported.length(); i++) {
                        Object value = supported.get(i);
                        require(value instanceof String && ((String)value).matches("[a-z.]{1,64}"));
                        commands.add((String)value);
                    }
                    break;
                default: throw new Failure(FailureKind.MALFORMED);
            }
        }
        ready = parsedReady;
        checks = Collections.unmodifiableList(parsedChecks);
        sessions = Collections.unmodifiableList(parsedSessions);
        supportedCommands = Collections.unmodifiableList(commands);
    }

    public static ApiReply parse(int exitCode, String stdout, String expectedCommand) throws Failure {
        if (exitCode == 255) throw new Failure(FailureKind.CONNECTION);
        if (exitCode == 124) throw new Failure(FailureKind.TIMEOUT);
        if (exitCode == 126 || exitCode == 127) throw new Failure(FailureKind.UNSUPPORTED_CLI);
        if (stdout == null || stdout.isBlank()) {
            throw new Failure(exitCode == 2 ? FailureKind.UNSUPPORTED_CLI : FailureKind.MALFORMED);
        }
        if (stdout.length() > MAX_BYTES || stdout.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES)
            throw new Failure(FailureKind.MALFORMED);
        try {
            require(expectedCommand != null);
            require(Set.of("doctor", "session.list", "capabilities").contains(expectedCommand));
            // JSONTokener is lenient, so require an object boundary and no trailing data.
            require(stdout.stripLeading().startsWith("{"));
            checkDepth(stdout);
            JSONTokener tokens = new JSONTokener(stdout);
            Object root = tokens.nextValue();
            require(root instanceof JSONObject && tokens.nextClean() == 0);
            ApiReply reply = new ApiReply((JSONObject)root, expectedCommand);
            require(reply.ok ? exitCode == 0 : (exitCode == 1 || exitCode == 2));
            return reply;
        } catch (JSONException | IllegalArgumentException error) {
            // Never attach the parser exception: it may quote a private response.
            throw new Failure(FailureKind.MALFORMED);
        }
    }

    private static void require(boolean valid) throws Failure {
        if (!valid) throw new Failure(FailureKind.MALFORMED);
    }

    private static void checkDepth(String text) throws Failure {
        int depth = 0;
        boolean quoted = false, escaped = false;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (escaped) { escaped = false; continue; }
            if (quoted && c == '\\') { escaped = true; continue; }
            if (c == '"') { quoted = !quoted; continue; }
            if (!quoted) {
                if (c == '{' || c == '[') require(++depth <= 32);
                if (c == '}' || c == ']') require(--depth >= 0);
            }
        }
        require(depth == 0 && !quoted);
    }

    private static String string(JSONObject object, String key, int limit) throws JSONException, Failure {
        Object value = object.get(key);
        require(value instanceof String && !((String)value).isEmpty() && ((String)value).length() <= limit);
        return (String)value;
    }

    private static boolean bool(JSONObject object, String key) throws JSONException, Failure {
        Object value = object.get(key);
        require(value instanceof Boolean);
        return (Boolean)value;
    }

    private static int integer(JSONObject object, String key, int minimum) throws JSONException, Failure {
        Object value = object.get(key);
        require(value instanceof Integer || value instanceof Long);
        long number = ((Number)value).longValue();
        require(number >= minimum && number <= Integer.MAX_VALUE);
        return (int)number;
    }
}
