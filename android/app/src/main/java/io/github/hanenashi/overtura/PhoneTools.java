package io.github.hanenashi.overtura;

/** A fixed, read-only Termux check; its output never includes paths or keys. */
final class PhoneTools {
    static final String COMMAND = "for tool in ssh timeout nano; do "
        + "if command -v \"$tool\" >/dev/null 2>&1; then "
        + "printf '%s ok\\n' \"$tool\"; else printf '%s missing\\n' \"$tool\"; fi; done";

    final boolean ssh;
    final boolean timeout;
    final boolean nano;

    private PhoneTools(boolean ssh, boolean timeout, boolean nano) {
        this.ssh = ssh;
        this.timeout = timeout;
        this.nano = nano;
    }

    static PhoneTools parse(int exitCode, String output) {
        if (exitCode != 0 || output == null) throw new IllegalArgumentException("Tool check failed");
        String[] lines = output.split("\\n", -1);
        if (lines.length != 4 || !lines[3].isEmpty())
            throw new IllegalArgumentException("Unexpected tool check output");
        return new PhoneTools(value(lines[0], "ssh"), value(lines[1], "timeout"),
            value(lines[2], "nano"));
    }

    private static boolean value(String line, String tool) {
        if (line.equals(tool + " ok")) return true;
        if (line.equals(tool + " missing")) return false;
        throw new IllegalArgumentException("Unexpected tool check output");
    }
}
