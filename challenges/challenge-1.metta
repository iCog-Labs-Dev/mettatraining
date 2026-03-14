;; ----------------------------------------------------------
;; CHALLENGE 1: Conditional Summation (The Filter)
;; ----------------------------------------------------------
;; TASK:
;; Write a higher-order function 'sumIf' that computes the sum 
;; of integers within an interval [a, b], but ONLY if those 
;; integers satisfy a specific condition.
;;
;; PARAMETERS:
;; $f         : A transformation function (e.g., identity 'id')
;; $condition : A function that returns a boolean (e.g., 'isEven')
;; $a         : The starting integer of the interval
;; $b         : The ending integer of the interval
;;
;; EXPECTED LOGIC:
;; For every integer 'i' from 'a' to 'b':
;;   If condition(i) is True  -> add f(i) to the total
;;   If condition(i) is False -> skip i
;;
;; SIGNATURE:
;; (= (sumIf $f $condition $a $b) ( ... ))
;;
;; TEST CASE:
;; !(sumIf id isEven 1 5) ; Should return 6 (2 + 4)

;; [INSERT SOLUTION HERE]
