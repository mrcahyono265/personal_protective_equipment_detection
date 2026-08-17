// ============================================
        // MODAL FUNCTIONS
        // ============================================
        function openModal(imageUrl, timestamp, status, zone) {
            const modal = document.getElementById('imageModal');
            const modalImage = document.getElementById('modalImage');
            const modalTimestamp = document.getElementById('modalTimestamp');
            const modalStatus = document.getElementById('modalStatus');
            const modalZone = document.getElementById('modalZone');
            
            modalImage.src = imageUrl;
            modalTimestamp.textContent = timestamp;
            modalStatus.textContent = status;
            modalZone.textContent = zone;
            
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Prevent background scroll
        }

        function closeModal() {
            const modal = document.getElementById('imageModal');
            modal.style.display = 'none';
            document.body.style.overflow = ''; // Restore scroll
        }

        // Close modal on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        });

        // Close modal when clicking outside image
        document.getElementById('imageModal').addEventListener('click', (e) => {
            if (e.target.id === 'imageModal') {
                closeModal();
            }
        });

        // ============================================
        // CORE FUNCTIONS
        // ============================================
        // Update current time
        function updateTime() {
            const now = new Date();
            document.getElementById('currentTime').textContent = 
                now.toLocaleTimeString('en-US', {hour12: false});
        }
        
        setInterval(updateTime, 1000);
        updateTime();

        // Zone change function
        async function changeZone(zoneName) {
            try {
                // Update button states
                document.querySelectorAll('.zone-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent.includes(zoneName)) {
                        btn.classList.add('active');
                    }
                });
                
                // Call API to change zone
                const response = await fetch(`/set_zone/${zoneName}`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Update display
                    document.getElementById('currentZoneDisplay').textContent = zoneName;
                    
                    // Show success feedback
                    addLogEntry({
                        timestamp: new Date().toLocaleTimeString('en-US', {hour12: false}),
                        zone: zoneName,
                        status: 'ZONE CHANGED',
                        person_id: 0,
                        image_url: null
                    }, 'info');
                }
            } catch (error) {
                console.error('Error changing zone:', error);
            }
        }

        // Add log entry to the UI with image support
        function addLogEntry(log, className = 'info') {
            const logContainer = document.getElementById('logContainer');
            
            // Determine CSS class based on status
            let logClass = 'info';
            if (log.status.includes('CRITICAL')) logClass = 'critical';
            else if (log.status.includes('VIOLATION')) logClass = 'violation';
            else if (log.status.includes('DISTRACTED')) logClass = 'distracted';
            else if (log.status.includes('SAFE')) logClass = 'safe';
            
            // Create log card
            const logCard = document.createElement('div');
            logCard.className = `log-card ${logClass}`;
            
            // Build HTML content
            let logHTML = `
                <div class="log-time">
                    <i class="far fa-clock"></i>
                    <span>${log.timestamp}</span>
                </div>
                <div class="log-content">
                    <div class="log-status">${log.status}</div>
                    ${log.person_id > 0 ? `<div class="log-person">Person ${log.person_id}</div>` : ''}
                </div>
                <div class="log-zone">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>Zone: ${log.zone}</span>
                </div>
            `;
            
            // Add snapshot thumbnail if image_url exists
            if (log.image_url) {
                logHTML += `
                    <div class="snapshot-container">
                        <div class="snapshot-label">
                            <i class="fas fa-camera"></i>
                            Violation Snapshot:
                        </div>
                        <img src="${log.image_url}" 
                             alt="Violation Snapshot" 
                             class="snapshot-thumbnail"
                             onclick="openModal('${log.image_url}', '${log.timestamp}', '${log.status}', '${log.zone}')">
                    </div>
                `;
            }
            
            logCard.innerHTML = logHTML;
            
            // Insert at the top
            logContainer.insertBefore(logCard, logContainer.firstChild);
            
            // Limit to 50 log entries
            const allLogs = logContainer.querySelectorAll('.log-card');
            if (allLogs.length > 50) {
                logContainer.removeChild(allLogs[allLogs.length - 1]);
            }
            
            // Update counters
            updateCounters();
            
            // Scroll to top
            logContainer.scrollTop = 0;
        }

        // Update counters
        function updateCounters() {
            const logContainer = document.getElementById('logContainer');
            const logs = logContainer.querySelectorAll('.log-card');
            
            document.getElementById('logCount').textContent = logs.length;
            
            // Count critical alerts
            const criticalCount = Array.from(logs).filter(log => 
                log.classList.contains('critical')
            ).length;
            
            // Count snapshots (logs with images)
            const snapshotCount = Array.from(logs).filter(log => 
                log.querySelector('.snapshot-thumbnail') !== null
            ).length;
            
            // Count active persons in current logs
            const activePersons = Array.from(logs).filter(log => 
                !log.classList.contains('info') && 
                !log.textContent.includes('ZONE CHANGED')
            ).length;
            
            document.getElementById('criticalCount').textContent = criticalCount;
            document.getElementById('totalDetections').textContent = logs.length - 1; // Subtract system log
            document.getElementById('snapshotCount').textContent = snapshotCount;
            document.getElementById('activePersons').textContent = Math.min(activePersons, 10); // Cap at 10 for display
        }

        // Fetch logs from server periodically
        async function fetchLogs() {
            try {
                const response = await fetch('/get_logs');
                const data = await response.json();
                
                if (data.logs && data.logs.length > 0) {
                    // Get current logs count to avoid duplicates
                    const currentLogs = document.querySelectorAll('.log-card').length;
                    
                    // Only add new logs (comparing with what we already have)
                    data.logs.slice(0, 5).forEach(log => {
                        // Check if this log already exists
                        const exists = Array.from(document.querySelectorAll('.log-time span'))
                            .some(timeSpan => timeSpan.textContent === log.timestamp && 
                                  document.querySelector('.log-status').textContent === log.status);
                        
                        if (!exists) {
                            addLogEntry(log);
                        }
                    });
                }
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        // Fetch snapshot stats
        async function fetchSnapshotStats() {
            try {
                const response = await fetch('/snapshot_stats');
                const data = await response.json();
                
                if (data.total_snapshots) {
                    // Update counter in stats grid
                    const snapshotElement = document.getElementById('snapshotCount');
                    if (snapshotElement) {
                        snapshotElement.textContent = data.total_snapshots;
                    }
                }
            } catch (error) {
                console.error('Error fetching snapshot stats:', error);
            }
        }

        // Get current zone on load
        async function loadCurrentZone() {
            try {
                const response = await fetch('/current_zone');
                const data = await response.json();
                
                if (data.current_zone) {
                    document.getElementById('currentZoneDisplay').textContent = data.current_zone;
                    
                    // Activate corresponding button
                    document.querySelectorAll('.zone-btn').forEach(btn => {
                        btn.classList.remove('active');
                        if (btn.textContent.includes(data.current_zone)) {
                            btn.classList.add('active');
                        }
                    });
                }
            } catch (error) {
                console.error('Error loading current zone:', error);
            }
        }

        // Video stream error handling
        const videoStream = document.getElementById('videoStream');
        const loadingIndicator = document.getElementById('loadingIndicator');
        
        videoStream.onloadstart = () => {
            loadingIndicator.style.display = 'flex';
        };
        
        videoStream.onload = () => {
            loadingIndicator.style.display = 'none';
        };
        
        videoStream.onerror = () => {
            loadingIndicator.style.display = 'flex';
            loadingIndicator.innerHTML = `
                <div class="spinner"></div>
                <p>Connection lost. Reconnecting...</p>
            `;
            
            // Try to reconnect after 3 seconds
            setTimeout(() => {
                videoStream.src = '/video_feed?' + new Date().getTime();
            }, 3000);
        };

        // ============================================
        // INITIALIZATION
        // ============================================
        document.addEventListener('DOMContentLoaded', () => {
            loadCurrentZone();
            updateCounters();
            
            // Fetch logs every 2 seconds
            setInterval(fetchLogs, 2000);
            
            // Fetch snapshot stats every 10 seconds
            setInterval(fetchSnapshotStats, 10000);
            
            // Initial fetches
            fetchLogs();
            fetchSnapshotStats();
            
            // Handle window resize for responsive behavior
            window.addEventListener('resize', () => {
                // Force reflow for scroll containers on resize
                const logContainer = document.getElementById('logContainer');
                if (logContainer) {
                    logContainer.style.overflowY = 'auto';
                }
            });
        });
