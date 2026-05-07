"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

Integration tests for `Graphiti.retrieve_episodes`.

Regression coverage for TASK-FIX-GET-EPISODES (`v0.29.5-guardkit.4`):
the MCP `get_episodes` tool was calling `EpisodicNode.get_by_group_ids`
directly with the shared driver, bypassing the `@handle_multiple_group_ids`
decorator. On FalkorDB's per-group named-graph layout that path queries
the wrong graph and returns []. The MCP tool now routes through
`Graphiti.retrieve_episodes`, which is decorated. These tests guard that
the decorator-routed path returns the expected episodes for both the
single-group and multi-group cases on FalkorDB, and that the Neo4j path
preserves `valid_at DESC` ordering (note: the underlying class method
ordering changed from `uuid DESC` to `valid_at DESC` as a side effect of
routing through the decorator).

Episodes are seeded with `EpisodicNode.save()` rather than
`Graphiti.add_episode()` to keep these tests hermetic w.r.t. LLM
credentials. The fix being tested is in the read path; seeding directly
exercises the same retrieval surface without coupling to LLM extraction.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from graphiti_core.cross_encoder import CrossEncoderClient
from graphiti_core.driver.driver import GraphProvider
from graphiti_core.embedder import EmbedderClient
from graphiti_core.graphiti import Graphiti
from graphiti_core.llm_client import LLMClient
from graphiti_core.nodes import EpisodeType, EpisodicNode
from tests.helpers_test import drivers, get_driver

pytestmark = pytest.mark.integration
pytest_plugins = ('pytest_asyncio',)


def _make_graphiti(driver) -> Graphiti:
    """Build a Graphiti instance with mock clients.

    `retrieve_episodes` only touches the graph driver, so mock LLM /
    embedder / cross-encoder clients are sufficient and let the test run
    without an OpenAI API key.
    """
    return Graphiti(
        graph_driver=driver,
        llm_client=Mock(spec=LLMClient),
        embedder=Mock(spec=EmbedderClient),
        cross_encoder=Mock(spec=CrossEncoderClient),
    )


def _make_episode(group_id: str, valid_at: datetime, name: str) -> EpisodicNode:
    return EpisodicNode(
        uuid=str(uuid4()),
        name=name,
        group_id=group_id,
        created_at=datetime.now(timezone.utc),
        source=EpisodeType.text,
        source_description='retrieve_episodes regression test',
        content=f'Episode content for {name}',
        valid_at=valid_at,
        entity_edges=[],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', drivers)
async def test_retrieve_episodes_single_group_falkordb(provider):
    """AC-IMP-EP-04: single-group write→read round-trip on FalkorDB.

    Fails on `v0.29.5-guardkit.3` (direct-driver path hits the wrong
    named graph and returns []) and passes on `.4` (decorator clones the
    driver to the per-group graph).
    """
    if provider != GraphProvider.FALKORDB:
        pytest.skip('FalkorDB-specific regression test')

    driver = get_driver(provider)
    group = f'retrieve_ep_test_{uuid4().hex[:8]}'

    try:
        # Seed an episode in the per-group graph
        valid_at = datetime.now(timezone.utc)
        episode = _make_episode(group, valid_at, 'single-group episode')
        # FalkorDB uses per-group named graphs; save through a cloned driver
        # so the episode lands in the same graph the decorator will read
        # from.
        per_group_driver = driver.clone(database=group)
        try:
            await episode.save(per_group_driver)
        finally:
            await per_group_driver.close()

        graphiti = _make_graphiti(driver)
        retrieved = await graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc) + timedelta(days=1),
            last_n=10,
            group_ids=[group],
        )

        assert any(ep.uuid == episode.uuid for ep in retrieved), (
            f'Expected episode {episode.uuid} in retrieved list; got '
            f'{[ep.uuid for ep in retrieved]}'
        )
    finally:
        await driver.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', drivers)
async def test_retrieve_episodes_multi_group_falkordb(provider):
    """AC-IMP-EP-05: multi-group retrieval merges per-group results.

    Verifies the decorator's `semaphore_gather` over per-group driver
    clones returns the union across groups.
    """
    if provider != GraphProvider.FALKORDB:
        pytest.skip('FalkorDB-specific regression test')

    driver = get_driver(provider)
    group_x = f'retrieve_ep_x_{uuid4().hex[:8]}'
    group_y = f'retrieve_ep_y_{uuid4().hex[:8]}'

    try:
        valid_at = datetime.now(timezone.utc)
        episode_x = _make_episode(group_x, valid_at, 'episode in X')
        episode_y = _make_episode(group_y, valid_at, 'episode in Y')

        for group, episode in ((group_x, episode_x), (group_y, episode_y)):
            per_group = driver.clone(database=group)
            try:
                await episode.save(per_group)
            finally:
                await per_group.close()

        graphiti = _make_graphiti(driver)
        retrieved = await graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc) + timedelta(days=1),
            last_n=10,
            group_ids=[group_x, group_y],
        )

        retrieved_uuids = {ep.uuid for ep in retrieved}
        assert episode_x.uuid in retrieved_uuids
        assert episode_y.uuid in retrieved_uuids
    finally:
        await driver.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('provider', drivers)
async def test_retrieve_episodes_valid_at_ordering_neo4j(provider):
    """AC-IMP-EP-06: Neo4j returns episodes ordered by `valid_at DESC`.

    Regression guard for the `uuid DESC` → `valid_at DESC` ordering
    change introduced when routing through `retrieve_episodes`.
    """
    if provider != GraphProvider.NEO4J:
        pytest.skip('Neo4j-specific ordering regression test')

    driver = get_driver(provider)
    group = f'retrieve_ep_order_{uuid4().hex[:8]}'

    try:
        base = datetime.now(timezone.utc)
        oldest = _make_episode(group, base - timedelta(hours=2), 'oldest')
        middle = _make_episode(group, base - timedelta(hours=1), 'middle')
        newest = _make_episode(group, base, 'newest')

        # Save in shuffled order so any natural insertion ordering can't
        # masquerade as valid_at ordering.
        for episode in (middle, oldest, newest):
            await episode.save(driver)

        graphiti = _make_graphiti(driver)
        retrieved = await graphiti.retrieve_episodes(
            reference_time=base + timedelta(days=1),
            last_n=10,
            group_ids=[group],
        )

        relevant = [ep for ep in retrieved if ep.uuid in {oldest.uuid, middle.uuid, newest.uuid}]
        assert len(relevant) == 3, f'Expected 3 seeded episodes; got {[ep.uuid for ep in relevant]}'
        assert relevant[0].uuid == newest.uuid
        assert relevant[1].uuid == middle.uuid
        assert relevant[2].uuid == oldest.uuid
    finally:
        await driver.close()
