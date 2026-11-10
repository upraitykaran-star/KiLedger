package com.taskmate.config;

import java.io.*;
import java.nio.file.*;
import java.util.Properties;

public record DatabaseConfig(String url, String user, String password) {
    public static DatabaseConfig load() throws IOException {
        Properties p = new Properties(); Path file = Path.of("taskmate.properties");
        if (Files.exists(file)) try (InputStream in = Files.newInputStream(file)) { p.load(in); }
        String url = value("TASKMATE_DB_URL", p.getProperty("db.url"));
        String user = value("TASKMATE_DB_USER", p.getProperty("db.user"));
        String password = value("TASKMATE_DB_PASSWORD", p.getProperty("db.password"));
        if (url == null || user == null || password == null || password.equals("CHANGE_ME"))
            throw new IOException("Database configuration is missing. Copy .env.example to taskmate.properties and set db.url, db.user, and db.password.");
        return new DatabaseConfig(url, user, password);
    }
    private static String value(String env, String fallback) { String v=System.getenv(env); return v == null || v.isBlank() ? fallback : v; }
}
