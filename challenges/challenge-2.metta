;; ----------------------------------------------------------
;; CHALLENGE 2: The General Accumulator
;; ----------------------------------------------------------
;; TASK:
;; Create a universal higher-order function 'accumulate'. 
;; Notice that 'sum' and 'product' are almost identical 
;; processes. This function should abstract that process.
;;
;; PARAMETERS:
;; $combiner  : The function used to join two numbers (e.g., + or *)
;; $baseCase  : The value to return when the interval is exhausted (a > b)
;; $f         : A transformation function applied to each term
;; $a         : Start of interval
;; $b         : End of interval
;;
;; SIGNATURE:
;; (= (accumulate $combiner $baseCase $f $a $b) ( ... ))
;;
;; TEST CASE:
;; !(accumulate + 0 id 1 4) ; Should return 10
