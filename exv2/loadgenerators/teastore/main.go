package main

import (
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

// RequestCounter keeps track of the number of requests per second.
type RequestCounter struct {
	mu    sync.Mutex
	count int
	total int
}

// Increment increments the request count.
func (rc *RequestCounter) Increment() {
	rc.mu.Lock()
	rc.count++
	rc.total++
	rc.mu.Unlock()
}

// Increment increments the request count.
func (rc *RequestCounter) FullReset() {
	rc.mu.Lock()
	rc.count = 0
	rc.total = 0
	rc.mu.Unlock()
}

// Reset resets the request count and returns the previous count.
func (rc *RequestCounter) Reset() int {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	count := rc.count
	rc.count = 0
	return count
}

func main() {
	counter := &RequestCounter{}

	c := make(chan os.Signal, 2)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		lastTime := time.Now()
		for _ = range c {
			now := time.Now()
			if now.Sub(lastTime) < 2*time.Second {
				os.Exit(0)
			}
			// sig is a ^C, handle it
			counter.FullReset()
			lastTime = now
		}
	}()

	// Start a goroutine to print the number of requests per second.
	go func() {
		for {
			time.Sleep(1 * time.Second)
			count := counter.Reset()
			log.Printf("Requests per second: %d / %d\n", count, counter.total)
		}
	}()

	// Handler function to handle all incoming HTTP requests.
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Increment the request counter.
		counter.Increment()

		// Sleep for one second before responding.
		time.Sleep(1 * time.Second)

		// Write a 200 status code response.
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Define the port to listen on.
	port := ":8000"

	// Log the starting of the server.
	log.Printf("Starting server on port %s", port)

	// Start the HTTP server.
	err := http.ListenAndServe(port, nil)
	if err != nil {
		log.Fatalf("Could not start server: %s", err)
	}
}
