package com.taskmate.utils;
import com.taskmate.database.Database; public class DbCheck { public static void main(String[] args){try(var c=Database.connect();var s=c.createStatement();var r=s.executeQuery("SELECT VERSION()")){r.next();System.out.println("MySQL connection OK: "+r.getString(1));}catch(Exception e){System.err.println(e.getMessage());System.exit(1);}} }
