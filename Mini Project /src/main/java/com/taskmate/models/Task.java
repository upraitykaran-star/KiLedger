package com.taskmate.models;
import java.time.LocalDate;
public record Task(long id, String title, String course, String type, LocalDate dueDate, String priority, double maxMarks, String status, Double marks, String feedback, String faculty) {}
