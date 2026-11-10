package com.taskmate;
import com.taskmate.models.Task;import com.taskmate.services.TaskService;import org.junit.jupiter.api.Test;import java.time.LocalDate;import static org.junit.jupiter.api.Assertions.*;
class TaskStatusTest {
 private Task t(LocalDate due,String status){return new Task(1,"t","c","ASSIGNMENT",due,"MEDIUM",10,status,null,null,"f");}
 @Test void evaluatedIsNotOverdue(){assertEquals("Completed",new TaskService().taskStatus(t(LocalDate.now().minusDays(1),"EVALUATED")));}
 @Test void pastPendingIsOverdue(){assertEquals("Overdue",new TaskService().taskStatus(t(LocalDate.now().minusDays(1),"PENDING")));}
 @Test void submittedIsNotOverdue(){assertEquals("Submitted",new TaskService().taskStatus(t(LocalDate.now().minusDays(1),"SUBMITTED")));}
}
