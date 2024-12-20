(ns cljdetector.core
  (:require [clojure.string :as string]
            [cljdetector.process.source-processor :as source-processor]
            [cljdetector.process.expander :as expander]
            [cljdetector.storage.storage :as storage]))

(def DEFAULT-CHUNKSIZE 5)
(def source-dir (or (System/getenv "SOURCEDIR") "/tmp"))
(def source-type #".*\.java")

(defn ts-println [& args]
  (let [timestamp (.toString (java.time.LocalDateTime/now))]
    (println args)
    ;; Log the message to the database
    (storage/add-update! {:timestamp timestamp :message (string/join " " args)})))


(defn maybe-clear-db [args]
  (when (some #{"CLEAR"} (map string/upper-case args))
      (ts-println "Clearing database...")
      (storage/clear-db!)))

(defn maybe-read-files [args]
  (when-not (some #{"NOREAD"} (map string/upper-case args))
    (let [start-time (System/nanoTime)]
      (ts-println "Reading and Processing files...")
      (let [chunk-param (System/getenv "CHUNKSIZE")
            chunk-size (if chunk-param (Integer/parseInt chunk-param) DEFAULT-CHUNKSIZE)
            file-handles (source-processor/traverse-directory source-dir source-type)
            chunks (source-processor/chunkify chunk-size file-handles)]
        (ts-println "Storing files...")
        (storage/store-files! file-handles)
        (let [end-time (System/nanoTime)
              duration (- end-time start-time)]
          (storage/add-update! {:timestamp (.toString (java.time.LocalDateTime/now))
                                :step "storing-files"
                                :duration duration}))
        (ts-println "Storing chunks of size" chunk-size "...")
        (let [start-time-2 (System/nanoTime)]
          (storage/store-chunks! chunks)
          (let [end-time-2 (System/nanoTime)
                duration-2 (- end-time-2 start-time-2)]
            (storage/add-update! {:timestamp (.toString (java.time.LocalDateTime/now))
                                  :step "storing-chunks"
                                  :duration duration-2}))))
      (let [end-time (System/nanoTime)
            duration (- end-time start-time)]
        (storage/add-update! {:timestamp (.toString (java.time.LocalDateTime/now))
                              :step "total-file-processing-time"
                              :duration duration})))))

(defn maybe-detect-clones [args]
  (when-not (some #{"NOCLONEID"} (map string/upper-case args))
    ;; Clone detection (identify-candidates)
    (let [start-time (System/nanoTime)]
      (ts-println "Identifying Clone Candidates...")
      (storage/identify-candidates!)
      (ts-println "Expanding Candidates...")
      (expander/expand-clones)
      (let [end-time (System/nanoTime)
            duration (- end-time start-time)]
        (storage/add-update! {:timestamp (.toString (java.time.LocalDateTime/now))
                              :step "total-match-time"
                              :duration duration})))))

(defn pretty-print [clones]
  (doseq [clone clones]
    (println "====================\n" "Clone with" (count (:instances clone)) "instances:")
    (doseq [inst (:instances clone)]
      (println "  -" (:fileName inst) "startLine:" (:startLine inst) "endLine:" (:endLine inst)))
    (println "\nContents:\n----------\n" (:contents clone) "\n----------")))

(defn maybe-list-clones [args]
  (when (some #{"LIST"} (map string/upper-case args))
    (ts-println "Consolidating and listing clones...")
    (pretty-print (storage/consolidate-clones-and-source))))



(defn -main
  "Starting Point for All-At-Once Clone Detection
  Arguments:
   - Clear clears the database
   - NoRead do not read the files again
   - NoCloneID do not detect clones
   - List print a list of all clones"
  [& args]

  (maybe-clear-db args)
  (maybe-read-files args)
  (maybe-detect-clones args)
  (maybe-list-clones args)
  (ts-println "Summary")
  (storage/print-statistics))
