; ==========================================================
; WARM-UP: THE BUILT-INS USED BY THE ROUTE SEARCH
; ----------------------------------------------------------
; Run this before bfs-shortest-path.metta:
;
;   metta builtins-warmup.metta
;
; Six built-ins do all the work there. None of them needs a
; hand-written recursive function.
; ==========================================================

; ----------------------------------------------------------
; 0. Set-up  (read the note, it explains the odd ordering)
; ----------------------------------------------------------
; In hyperon, any (= ...) definition written AFTER a `!` statement
; in the same file gets loaded TWICE, which silently doubles every
; result. So definitions and plain facts go at the top, and every
; `!` query goes below them. You will see the same layout in
; bfs-shortest-path.metta.

; A tiny 4-city line:  A - B - C - D
(Link A B) (Link B A)
(Link B C) (Link C B)
(Link C D) (Link D C)

; This is the REAL route search from bfs-shortest-path.metta,
; unchanged, on a four-city graph. Come back to it after section 4 --
; by then every piece will be familiar.
;
;   $routeSoFar      route built so far, doubling as the visited set
;   $currentCity     where the route has reached
;   $remainingDepth  how many more legs this branch may take
(= (getRoutes $routeSoFar $currentCity $destination $remainingDepth)
   (if (== $currentCity $destination)
       $routeSoFar
       (if (== $remainingDepth 0)
           (empty)
           (match &self (Link $currentCity $nextCity)
             (if (== (intersection-atom $routeSoFar ($nextCity)) ())
                 (getRoutes (union-atom $routeSoFar ($nextCity))
                            $nextCity
                            $destination
                            (- $remainingDepth 1))
                 (empty))))))

; ----------------------------------------------------------
; 1. An expression is a list
; ----------------------------------------------------------
; union-atom joins two expressions end to end. We use it to add
; one city to a route, by joining a one-element expression.

!(union-atom (Addis Cairo) (London))
; => (Addis Cairo London)

!(union-atom (Addis) (Cairo))
; => (Addis Cairo)

; car-atom takes the first element. We use it to pick one route
; out of all the routes found.
!(car-atom ((Addis Cairo) (Addis London)))
; => (Addis Cairo)

; unique-atom removes duplicates from an expression.
!(unique-atom (Addis Cairo Addis))
; => (Addis Cairo)

; ----------------------------------------------------------
; 2. intersection-atom as a membership test
; ----------------------------------------------------------
; What the two expressions have in common. Wrap the thing you are
; looking for in its own expression, and () means "not present".
; This is how the search avoids walking in circles.

!(intersection-atom (Addis Cairo London) (Cairo))
; => (Cairo)

!(intersection-atom (Addis Cairo London) (Tokyo))
; => ()

; So the test reads:  is Tokyo NOT already on this route?
!(== (intersection-atom (Addis Cairo London) (Tokyo)) ())
; => True

; ----------------------------------------------------------
; 3. Many answers at once
; ----------------------------------------------------------
; superpose turns an expression into several separate answers.
; Everything downstream then runs once per answer -- this is
; MeTTa's replacement for a loop.

!(superpose (Addis Cairo London))
; => Addis, Cairo, London

; collapse does the reverse: it gathers many answers back into one
; expression, so you can count them or test for none.
!(collapse (superpose (Addis Cairo London)))
; => (Addis Cairo London)

; unique drops repeated answers. Note the order is not preserved --
; a set of answers has no order, so never rely on it.
!(unique (superpose (Addis Cairo Addis)))
; => Cairo, Addis

; empty produces NO answer at all. Use it to throw a branch away.
!(collapse (empty))
; => ()

; ----------------------------------------------------------
; 4. Reading the space
; ----------------------------------------------------------
; match takes a space, a pattern, and what to return. It answers
; once per matching atom -- non-deterministically, exactly like
; superpose.

!(match &self (Link B $x) $x)
; => A, C

; Collapse it when you want the answers as one expression.
!(collapse (match &self (Link B $x) $x))
; => (A C)

; A city with no links gives (), which is how the real search
; detects somewhere unreachable.
!(collapse (match &self (Link Z $x) $x))
; => ()

; ----------------------------------------------------------
; 5. All of them together
; ----------------------------------------------------------
; `getRoutes` at the top of this file uses every one of them: match to
; find the next city, intersection-atom to reject cities already
; visited, union-atom to extend the route, empty to abandon a dead
; branch, and collapse to gather what survived.

!(collapse (getRoutes (A) A D 3))
; => ((A B C D))

; Ask for a route that is too short to exist and you get (),
; which is the signal to try one leg deeper.
!(collapse (getRoutes (A) A D 2))
; => ()
