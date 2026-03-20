;; ==========================================================
;; CHALLENGE 11: Find Even Elements
;; ----------------------------------------------------------
;; TASK:
;; Write a function 'find-even' that takes a list of numbers
;; $list and returns a new list containing only the even numbers.
;;
;; APPROACH:
;; Base case: empty list.
;; Recursive step: check car for evenness;
;;   if even, cons it onto recursive result; otherwise skip.
;;
;; SIGNATURE:
;; (= (find-even $list) ( ... ))
;;
;; TEST CASE:
;; !(find-even (3 8 5 10 7 12)) ; Should return (8 10 12)
