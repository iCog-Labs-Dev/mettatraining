;; ----------------------------------------------------------
;; CHALLENGE 14: Count Valid Pending Tasks
;; ----------------------------------------------------------
;; TASK:
;; Given $queue and $banned, where the first item in $queue is
;; processing and the rest are pending, return the number of
;; pending tasks that are not banned.
;;
;; APPROACH:
;; 1. Extract pending tasks: 
;; 2. Remove banned tasks: 
;; 3. Return count: 
;;
;; SIGNATURE:
;; (= (count-valid-pending $queue $banned) ( ... ))
;;
;; TEST CASE:
;; !(count-valid-pending (Task1 Task2 Task3 Task4) (Task3)) ; Should return 2
