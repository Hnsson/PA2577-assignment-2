(ns cljdetector.process.source-processor
  (:use [clojure.java.io])
  (:require [clojure.string :as string]
            [clj-commons.digest :as digest]
            [cljdetector.storage.storage :as storage]))


(def emptyLine (re-pattern "^\\s*$"))
(def oneLineComment (re-pattern "//.*"))
(def oneLineMultiLineComment (re-pattern "/\\*.*?\\*/"))
(def openMultiLineComment (re-pattern "/\\*+[^*/]*$"))
(def closeMultiLineComment (re-pattern "^[^*/]*\\*+/"))

(defn process-lines [lines]
  (drop 1
        (reduce (fn [collection item]
                  (conj collection
                        (let [index (+ 1 (:lineNumber (last collection)))]
                          (cond
                            (and (= (:lineType (last collection)) "multiLineComment") 
                                 (re-matches closeMultiLineComment item)) {:lineNumber index :contents (string/trim (string/replace item closeMultiLineComment "")) :lineType "lastMultiLineComment"}
                            (= (:lineType (last collection)) "multiLineComment") {:lineNumber index :contents "" :lineType "multiLineComment"}
                            (re-matches emptyLine item) {:lineNumber index :contents "" :lineType "emptyLine"}
                            (re-matches oneLineComment item) {:lineNumber index :contents (string/trim (string/replace item oneLineComment "")) :lineType "oneLineComment"}
                            (re-matches oneLineMultiLineComment item) {:lineNumber index :contents (string/trim (string/replace item oneLineMultiLineComment "")) :lineType "oneLineMultiLineComment"}
                            (re-matches openMultiLineComment item) {:lineNumber index :contents (string/trim (string/replace item openMultiLineComment "")) :lineType "multiLineComment"}
                            :else {:lineNumber index :contents (string/trim item) :lineType "normal"}
                            )))) [{:lineNumber 0 :contents "" :lineType "startLine"}] lines)))


;; (defn chunkify-file [chunkSize file]
;;   (try (let [fileName (.getPath file)
;;              filteredLines (filter #(not (= "" (:contents %)))
;;                                    (-> file
;;                                        slurp
;;                                        (string/split #"\n")
;;                                        process-lines))
;;              iterator (range (- (count filteredLines) chunkSize))]
;;          (map (fn [%]
;;                 (let [chunk (take chunkSize (nthrest filteredLines %))
;;                       startLine (:lineNumber (first chunk))
;;                       endLine (:lineNumber (last chunk))
;;                       hash (digest/md5 (string/join "\n" (map :contents chunk)))]
;;                   {:fileName fileName :startLine startLine :endLine endLine :chunkHash hash}))
;;               iterator))
;;        (catch Exception e [])))

(defn chunkify-file [chunkSize file]
  (let [start-time (System/nanoTime)] ;; Start timing
    (try
      (let [fileName (.getPath file)
            filteredLines (filter #(not (= "" (:contents %)))
                                  (-> file
                                      slurp
                                      (string/split #"\n")
                                      process-lines))
            iterator (range (- (count filteredLines) chunkSize))]
        ;; Generate chunks
        (let [chunks (map (fn [%]
                            (let [chunk (take chunkSize (nthrest filteredLines %))
                                  startLine (:lineNumber (first chunk))
                                  endLine (:lineNumber (last chunk))
                                  hash (digest/md5 (string/join "\n" (map :contents chunk)))]
                              {:fileName fileName :startLine startLine :endLine endLine :chunkHash hash}))
                          iterator)]
          ;; Log processing time per file
          (let [end-time (System/nanoTime)
                duration (- end-time start-time)
                chunks-count (count chunks)]
            (storage/add-update! {:timestamp (.toString (java.time.LocalDateTime/now))
                                  :step "chunkify-file"
                                  :duration duration
                                  :fileName fileName
                                  :chunks-count chunks-count
                                  :time-per-chunk (/ duration (max 1 chunks-count))})
            chunks)))
      (catch Exception e
        (println "Error processing file:" (.getPath file) (.getMessage e))
        []))))


(defn chunkify [chunkSize files]
  (map #(chunkify-file chunkSize %) files))

(defn traverse-directory [path pattern]
  (filter #(re-matches pattern (.getName %)) (file-seq (file path))))
