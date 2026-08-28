(= (sharedFeature $movie $candidate $space)
   (match $space
      (, (movie-feature $movie $kind $value)
         (movie-feature $candidate $kind $value))
      $kind))

(= (moviesLike $movie $space)
   (sharedFeature $movie $candidate $space))

(= (moviesWithFeature $kind $value $space)
   (match $space
      (movie-feature $movie $kind $value)
      $movie))

(= (weight Genre) 4)
(= (weight Theme) 3)
(= (weight Tone) 2)
(= (weight Setting) 1)
(= (weight Era) 1)

(= (fold $fn $acc $list)
   (if (== $list ())
     $acc
     (let* (
            (($h $t) (decons-atom $list))
            ($acc' ($fn $acc $h))
            )
       (fold $fn $acc' $t)
       )
     )
   )

(= (scoreMovieLike $movie $candidate $space)
   (fold + 0
      (collapse
         (weight 
           (sharedFeature $movie $candidate $space)
           )
         )
      )
)

(= (scoreCandidateFromLikes $candidate $likedMovies $space)
   (if (== $likedMovies ())
     0
     (let* (
      (($likedMovie $rest) (decons-atom $likedMovies))
      ($score (scoreMovieLike $likedMovie $candidate $space))
      )
      (+ $score (scoreCandidateFromLikes $candidate $rest $space))
      )
     )
   )

(= (doesCandidateHavePrefFeats $candidate $value $space) ; does the candidate have the prefered feature?
   (fold + 0
            (collapse
               (match $space
                  (movie-feature $candidate $kind $value)
                  (weight $kind)))
    )
   )

(= (scoreCandidateFromPrefs $candidate $prefs $space)
   (if (== $prefs ())
     0
     (let* (
            (($kind $restWithValue) (decons-atom $prefs))
            (($value $rest) (decons-atom $restWithValue))
            ($score (doesCandidateHavePrefFeats $candidate $value $space))
      )
      (+ $score (scoreCandidateFromPrefs $candidate $rest $space))
      )
     )
   )
