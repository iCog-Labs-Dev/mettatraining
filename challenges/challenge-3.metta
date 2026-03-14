;; ----------------------------------------------------------
;; CHALLENGE 3: The "Digit Counter"
;; ----------------------------------------------------------
;; TASK:
;; Write a function that calculates how many digits exist 
;; in a given positive integer.
;;
;; LOGIC:
;; 1. Use an accumulator ($count) to keep track of digits.
;; 2. Remove one digit at a time by performing integer 
;;    division by 10 (/ $number 10).
;; 3. Increment the $count for every removal.
;; 4. Stop when the number becomes 0.
;;
;; SIGNATURE:
;; (= (count-digits $number $count) ( ... ))
;;
;; TEST CASE:
;; !(count-digits 90721 0) ; Should return 5
