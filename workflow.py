"""Lesson-specific workflow. Read this file before the execution adapter."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from runtime import atomic_json, contained_path, in_process_tool

async def run(agent, data):
    proposals = []
    for contractor in data['contractors']:
        proposal = await agent.ask('bid_' + contractor['id'], 'Respond to the task CFP using only your declared capability and cost.',
            {'cfp': data['task'], 'profile': contractor}, {'contractor': contractor['id'], 'skill': contractor['skill'], 'cost': contractor['cost']})
        if proposal['contractor'] != contractor['id'] or proposal['skill'] != contractor['skill'] or proposal['cost'] < 0:
            raise ValueError('Bid identity or capability does not match the registry')
        proposals.append(proposal)
    eligible = [p for p in proposals if p['skill'] == data['required_skill'] and p['cost'] <= data['budget']]
    if not eligible:
        return {'status': 'no_award', 'proposals': proposals}
    winner = min(eligible, key=lambda p: (p['cost'], p['contractor']))
    result = await agent.ask('awarded_' + winner['contractor'], 'Complete the awarded task without external side effects.', {'task': data['task'], 'award': winner}, 'Prepared a local evidence brief.')
    return {'status': 'completed', 'winner': winner, 'rejected': [p['contractor'] for p in proposals if p != winner], 'result': result}
