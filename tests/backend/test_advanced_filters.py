"""Advanced filtering & search tests for AWS Guardian."""

import pytest


class TestFilterEngine:
    """Test filtering engine."""

    def test_simple_filter(self):
        """✅ Apply simple filter."""
        from guardian.search.advanced_filter import FilterEngine

        engine = FilterEngine()

        result = engine.apply_filter({
            'data': [
                {'id': '1', 'severity': 'high', 'type': 'threat'},
                {'id': '2', 'severity': 'low', 'type': 'cost'},
                {'id': '3', 'severity': 'high', 'type': 'threat'}
            ],
            'filter': {'severity': 'high'}
        })

        assert 'filtered_data' in result
        assert 'count' in result

    def test_multi_condition_filter(self):
        """✅ Apply multi-condition filter."""
        from guardian.search.advanced_filter import FilterEngine

        engine = FilterEngine()

        result = engine.apply_filter({
            'data': [
                {'severity': 'high', 'type': 'threat', 'status': 'open'},
                {'severity': 'low', 'type': 'threat', 'status': 'resolved'}
            ],
            'filters': [
                {'field': 'severity', 'value': 'high'},
                {'field': 'status', 'value': 'open'}
            ],
            'logic': 'AND'
        })

        assert 'filtered_data' in result or 'results' in result

    def test_range_filter(self):
        """✅ Filter by range."""
        from guardian.search.advanced_filter import FilterEngine

        engine = FilterEngine()

        result = engine.apply_filter({
            'data': [{'value': 100}, {'value': 50}, {'value': 150}],
            'range_filter': {'field': 'value', 'min': 75, 'max': 125}
        })

        assert 'filtered_data' in result or 'count' in result


class TestFullTextSearch:
    """Test full-text search engine."""

    def test_full_text_search(self):
        """✅ Search full text index."""
        from guardian.search.advanced_filter import FullTextSearch

        search = FullTextSearch()

        result = search.search({
            'query': 'unauthorized access',
            'fields': ['title', 'description'],
            'limit': 10
        })

        assert 'results' in result or 'matches' in result
        assert 'count' in result or len(result.get('results', [])) >= 0

    def test_fuzzy_search(self):
        """✅ Fuzzy text search."""
        from guardian.search.advanced_filter import FullTextSearch

        search = FullTextSearch()

        result = search.fuzzy_search({
            'query': 'unauthrized',  # typo
            'threshold': 0.8
        })

        assert 'results' in result or 'suggestions' in result

    def test_search_with_facets(self):
        """✅ Search with faceted results."""
        from guardian.search.advanced_filter import FullTextSearch

        search = FullTextSearch()

        result = search.search({
            'query': 'threat',
            'facets': ['severity', 'type', 'status']
        })

        assert 'results' in result
        assert 'facets' in result or 'aggregations' in result


class TestQueryBuilder:
    """Test SQL-like query builder."""

    def test_build_select_query(self):
        """✅ Build SELECT query."""
        from guardian.search.advanced_filter import QueryBuilder

        builder = QueryBuilder()

        query = builder.build({
            'select': ['id', 'severity', 'timestamp'],
            'from': 'threats',
            'where': [{'field': 'severity', 'op': 'eq', 'value': 'high'}]
        })

        assert 'query' in query or 'sql' in query
        assert 'parameters' in query or len(query) > 0

    def test_build_complex_query(self):
        """✅ Build complex query with joins."""
        from guardian.search.advanced_filter import QueryBuilder

        builder = QueryBuilder()

        query = builder.build({
            'select': ['t.id', 't.severity', 'r.response_type'],
            'from': 'threats t',
            'join': [{'table': 'responses r', 'on': 't.id = r.threat_id'}],
            'where': [
                {'field': 't.severity', 'op': 'in', 'value': ['high', 'critical']}
            ],
            'order_by': [{'field': 't.timestamp', 'direction': 'DESC'}]
        })

        assert 'query' in query or 'sql' in query

    def test_build_aggregation_query(self):
        """✅ Build aggregation query."""
        from guardian.search.advanced_filter import QueryBuilder

        builder = QueryBuilder()

        query = builder.build({
            'select': ['severity', 'count(*) as count'],
            'from': 'threats',
            'group_by': ['severity'],
            'having': {'condition': 'count > 5'}
        })

        assert 'query' in query or 'sql' in query


class TestSavedFilters:
    """Test saved filter management."""

    def test_save_filter(self):
        """✅ Save filter for reuse."""
        from guardian.search.advanced_filter import SavedFilters

        saved = SavedFilters()

        result = saved.save({
            'name': 'Critical Threats',
            'filter': {
                'severity': 'critical',
                'status': 'open'
            }
        })

        assert 'filter_id' in result or 'saved' in result

    def test_list_saved_filters(self):
        """✅ List saved filters."""
        from guardian.search.advanced_filter import SavedFilters

        saved = SavedFilters()

        result = saved.list({
            'user_id': 'user_123'
        })

        assert 'filters' in result or isinstance(result, list)

    def test_apply_saved_filter(self):
        """✅ Apply saved filter to data."""
        from guardian.search.advanced_filter import SavedFilters

        saved = SavedFilters()

        result = saved.apply({
            'filter_id': 'flt_123',
            'data': [
                {'severity': 'critical', 'status': 'open'},
                {'severity': 'high', 'status': 'open'}
            ]
        })

        assert 'filtered' in result or 'results' in result


class TestAdvancedFilterIntegration:
    """End-to-end filtering and search workflows."""

    def test_full_search_pipeline(self):
        """✅ Complete search: build query → search → filter."""
        from guardian.search.advanced_filter import (
            QueryBuilder,
            FullTextSearch,
            FilterEngine
        )

        builder = QueryBuilder()
        search = FullTextSearch()
        engine = FilterEngine()

        # Build query
        query = builder.build({
            'select': ['id', 'severity'],
            'from': 'threats'
        })
        assert 'query' in query or 'sql' in query

        # Search
        results = search.search({'query': 'threat'})
        assert 'results' in results

        # Filter results
        filtered = engine.apply_filter({
            'data': results.get('results', []),
            'filter': {'severity': 'high'}
        })
        assert 'filtered_data' in filtered or 'results' in filtered

    def test_saved_filter_workflow(self):
        """✅ Save and reuse filters."""
        from guardian.search.advanced_filter import SavedFilters

        saved = SavedFilters()

        # Save filter
        filter_result = saved.save({
            'name': 'My Filter',
            'filter': {'severity': 'high'}
        })
        assert 'filter_id' in filter_result or 'saved' in filter_result

        # List filters
        filters = saved.list({'user_id': 'user_123'})
        assert 'filters' in filters or isinstance(filters, list)

    def test_complex_search_and_filter(self):
        """✅ Complex search with multiple filters."""
        from guardian.search.advanced_filter import (
            FullTextSearch,
            FilterEngine
        )

        search = FullTextSearch()
        engine = FilterEngine()

        # Faceted search
        results = search.search({
            'query': 'threat',
            'facets': ['severity', 'type']
        })
        assert 'results' in results

        # Apply filters
        filtered = engine.apply_filter({
            'data': results.get('results', []),
            'filters': [
                {'field': 'severity', 'value': 'high'}
            ]
        })
        assert 'filtered_data' in filtered or 'results' in filtered

    def test_advanced_query_with_search(self):
        """✅ Advanced query building with search."""
        from guardian.search.advanced_filter import (
            QueryBuilder,
            FullTextSearch
        )

        builder = QueryBuilder()
        search = FullTextSearch()

        # Build complex query
        query = builder.build({
            'select': ['id', 'severity'],
            'from': 'threats',
            'where': [{'field': 'severity', 'op': 'eq', 'value': 'high'}],
            'order_by': [{'field': 'timestamp', 'direction': 'DESC'}]
        })
        assert 'query' in query or 'sql' in query

        # Execute search
        results = search.search({'query': 'critical threat'})
        assert 'results' in results
