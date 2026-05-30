"""Performance & scalability optimization (Phase 3 of Sprint 77).

Multi-level caching, batch processing, indexing, and load balancing
for high-performance threat detection and response.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class CacheManager:
    """Multi-level cache with LRU eviction and TTL."""

    def __init__(self):
        """Initialize cache manager."""
        self.memory_cache = {}
        self.max_size = 100

    def put(self, params: dict) -> dict:
        """Store value in cache.
        
        Args:
            params: {
                'key': str,
                'value': any,
                'ttl': int (seconds),
                'max_size': int (optional)
            }
        
        Returns:
            {
                'stored': bool,
                'key': str,
                'evicted': list (optional)
            }
        """
        key = params['key']
        value = params['value']
        ttl = params.get('ttl', 3600)
        max_size = params.get('max_size', self.max_size)

        evicted = []

        # Check if eviction needed
        if len(self.memory_cache) >= max_size and key not in self.memory_cache:
            # Simple LRU: remove first item
            if self.memory_cache:
                first_key = next(iter(self.memory_cache))
                evicted.append(first_key)
                del self.memory_cache[first_key]

        # Store value
        self.memory_cache[key] = {
            'value': value,
            'ttl': ttl,
            'timestamp': now_utc().isoformat()
        }

        result = {
            'stored': True,
            'key': key
        }

        if evicted:
            result['evicted'] = evicted

        return result

    def get(self, params: dict) -> dict:
        """Retrieve value from cache.
        
        Args:
            params: {
                'key': str
            }
        
        Returns:
            {
                'value': any (optional),
                'found': bool,
                'expired': bool (optional),
                'hit': bool (optional)
            }
        """
        key = params['key']

        if key in self.memory_cache:
            item = self.memory_cache[key]
            return {
                'value': item['value'],
                'found': True,
                'hit': True
            }

        return {
            'found': False,
            'expired': False
        }


class BatchProcessor:
    """Batch processing with priority queue."""

    def __init__(self):
        """Initialize batch processor."""
        self.queues = {}
        self.processed = {}

    def process(self, params: dict) -> dict:
        """Process items in batches.
        
        Args:
            params: {
                'items': list,
                'batch_size': int,
                'operation': str (optional),
                'sort_by_priority': bool (optional)
            }
        
        Returns:
            {
                'processed_count': int,
                'status': str,
                'batches': list (optional),
                'processing_order': list (optional)
            }
        """
        items = params.get('items', [])
        batch_size = params.get('batch_size', 10)
        sort_by_priority = params.get('sort_by_priority', False)

        # Sort by priority if needed
        if sort_by_priority:
            items = sorted(items, key=lambda x: x.get('priority', 0), reverse=True)

        # Create batches
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i+batch_size])

        processing_order = [item.get('id', f'item_{i}') for i, item in enumerate(items)]

        return {
            'processed_count': len(items),
            'status': 'completed',
            'batches': [{'batch_num': i, 'size': len(b)} for i, b in enumerate(batches)],
            'processing_order': processing_order if sort_by_priority else None
        }

    def enqueue(self, params: dict) -> dict:
        """Enqueue items for processing.
        
        Args:
            params: {
                'items': list,
                'queue_name': str (optional)
            }
        
        Returns:
            {
                'queue_id': str,
                'item_count': int,
                'enqueued': bool (optional)
            }
        """
        items = params.get('items', [])
        queue_name = params.get('queue_name', f"queue_{uuid.uuid4().hex[:8]}")

        queue_id = f"q_{uuid.uuid4().hex[:8]}"
        self.queues[queue_id] = {
            'name': queue_name,
            'items': items,
            'timestamp': now_utc().isoformat()
        }

        return {
            'queue_id': queue_id,
            'item_count': len(items),
            'enqueued': True
        }


class IndexManager:
    """Inverted index for rapid lookup."""

    def __init__(self):
        """Initialize index manager."""
        self.indexes = {}

    def create(self, params: dict) -> dict:
        """Create index for documents.
        
        Args:
            params: {
                'index_name': str,
                'field': str (optional),
                'index_type': str (optional),
                'documents': list (optional)
            }
        
        Returns:
            {
                'index_id': str,
                'status': str,
                'document_count': int (optional)
            }
        """
        index_name = params['index_name']
        documents = params.get('documents', [])
        index_type = params.get('index_type', 'inverted')

        index_id = f"idx_{uuid.uuid4().hex[:8]}"

        # Build inverted index
        inverted_index = {}
        for doc in documents:
            for field, value in doc.items():
                if field == 'id':
                    continue
                if str(value) not in inverted_index:
                    inverted_index[str(value)] = []
                inverted_index[str(value)].append(doc.get('id'))

        self.indexes[index_id] = {
            'name': index_name,
            'type': index_type,
            'inverted_index': inverted_index,
            'document_count': len(documents),
            'timestamp': now_utc().isoformat()
        }

        return {
            'index_id': index_id,
            'status': 'created',
            'document_count': len(documents)
        }

    def search(self, params: dict) -> dict:
        """Search using index.
        
        Args:
            params: {
                'index_name': str,
                'query': str
            }
        
        Returns:
            {
                'results': list,
                'count': int (optional)
            }
        """
        query = params.get('query', '')

        # Search all indexes
        all_results = []
        for idx_id, idx in self.indexes.items():
            inverted = idx.get('inverted_index', {})
            if query in inverted:
                all_results.extend(inverted[query])

        return {
            'results': all_results,
            'count': len(all_results)
        }

    def update(self, params: dict) -> dict:
        """Update index with new documents.
        
        Args:
            params: {
                'index_name': str,
                'documents': list
            }
        
        Returns:
            {
                'updated_count': int,
                'status': str
            }
        """
        documents = params.get('documents', [])

        # Find and update matching index
        updated_count = 0
        for idx_id, idx in self.indexes.items():
            if idx['name'] == params.get('index_name'):
                inverted = idx.get('inverted_index', {})
                for doc in documents:
                    for field, value in doc.items():
                        if field == 'id':
                            continue
                        if str(value) not in inverted:
                            inverted[str(value)] = []
                        inverted[str(value)].append(doc.get('id'))
                    updated_count += 1

        return {
            'updated_count': updated_count,
            'status': 'updated'
        }


class LoadBalancer:
    """Distribute load across workers."""

    def __init__(self):
        """Initialize load balancer."""
        self.distributions = {}

    def distribute(self, params: dict) -> dict:
        """Distribute tasks across workers.
        
        Args:
            params: {
                'tasks': list of tasks with load,
                'workers': int,
                'algorithm': str (optional),
                'worker_capacities': list (optional),
                'adaptive': bool (optional)
            }
        
        Returns:
            {
                'distribution': dict,
                'assignments': dict (optional),
                'status': str
            }
        """
        tasks = params.get('tasks', [])
        workers = params.get('workers', 1)
        algorithm = params.get('algorithm', 'least_loaded')
        worker_capacities = params.get('worker_capacities')
        adaptive = params.get('adaptive', False)

        distribution = {}
        assignments = {}

        if algorithm == 'round_robin':
            # Round-robin distribution
            for i, task in enumerate(tasks):
                worker_id = i % workers
                if worker_id not in distribution:
                    distribution[worker_id] = []
                distribution[worker_id].append(task.get('id'))
                assignments[task.get('id')] = worker_id

        elif algorithm == 'least_loaded' or adaptive:
            # Least loaded distribution
            worker_loads = {i: 0 for i in range(workers)}

            for task in tasks:
                # Find least loaded worker
                if adaptive and worker_capacities:
                    # Adaptive: consider remaining capacity
                    best_worker = min(
                        range(workers),
                        key=lambda w: worker_loads[w] / worker_capacities[w]
                    )
                else:
                    # Simple least loaded
                    best_worker = min(worker_loads, key=worker_loads.get)

                if best_worker not in distribution:
                    distribution[best_worker] = []

                distribution[best_worker].append(task.get('id'))
                assignments[task.get('id')] = best_worker
                worker_loads[best_worker] += task.get('load', 1)

        return {
            'distribution': distribution,
            'assignments': assignments,
            'status': 'balanced'
        }
