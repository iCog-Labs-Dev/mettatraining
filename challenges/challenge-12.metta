;; ----------------------------------------------------------
;; CHALLENGE 12: Reverse a Given List (and Partial Reverse)
;; ----------------------------------------------------------
;; TASK:
;; Implement 'reverse-list' using recursion and
;; construction/deconstruction primitives.
;;
;; APPROACH:
;; Base case: empty list → ().
;; Recursive decomposition: push the head to the end of the
;; reversed tail until base case.
;;
;; SIGNATURE:
;; (= (reverse-list $list) ( ... ))
;;
;; TEST CASE:
;; !(reverse-list (A B C D)) ; Should return (D C B A)