import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from pathsnap.core import load_trip, candidates, project, reference_labels, Network, decode, probabilities

class PipelineTests(unittest.TestCase):
    def fixture(self, folder):
        folder = Path(folder)/'12345678'; folder.mkdir()
        np.savetxt(folder/'12345678.nodes', [[37,56],[37.001,56],[37.002,56],[37.003,56]])
        np.savetxt(folder/'12345678.arcs', [[0,1],[1,2],[2,3],[1,0]], fmt='%d')
        np.savetxt(folder/'12345678.track', [[37.0003,56.00001,1],[37.0013,56.00001,2],[37.0027,56.00001,3]])
        np.savetxt(folder/'12345678.route', [0,1,2], fmt='%d')
        return folder

    def test_exact_candidates_and_reference_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self.fixture(directory); trip = load_trip(folder); c = candidates(trip, 3)
            d, _, _ = project(trip.points[:,None,:], trip.xy[trip.arcs[:,0]], trip.xy[trip.arcs[:,1]])
            for t in range(len(d)):
                expected = np.lexsort((np.arange(len(trip.arcs)), d[t]))[:3]
                np.testing.assert_array_equal(c['ids'][t], expected)
            labels, _, _ = reference_labels(trip, folder)
            np.testing.assert_array_equal(labels, [0,1,2])
            self.assertTrue(np.isfinite(c['x']).all())

    def test_directed_shortest_path_and_viterbi(self):
        with tempfile.TemporaryDirectory() as directory:
            trip = load_trip(self.fixture(directory)); net = Network(trip)
            self.assertIn(3, net.search(0,1000.)[0])
            self.assertNotIn(0, net.search(3,1000.)[0])
            c = candidates(trip,4)
            p = np.full(c['ids'].shape, .01)
            for t, arc in enumerate([0,1,2]): p[t,c['ids'][t] == arc] = .97
            pred, _, _ = decode(trip,c,p)
            np.testing.assert_array_equal(pred,[0,1,2])
            trip.gps[2,2] = 1000
            self.assertEqual(decode(trip,c,p)[2], [2])

    def test_prediction_never_reads_reference(self):
        from pathsnap.api import infer
        with tempfile.TemporaryDirectory() as directory:
            folder = self.fixture(directory)
            class Scorer:
                def predict_proba(self,x):
                    p=np.exp(-x[:,0]/10)
                    return np.column_stack([1-p,p])
            with patch('pathsnap.api.assets', return_value=(Scorer(), {'candidate_k':4,'beta':30.,'gap_s':60.,'model_family':'test'})):
                before = infer(folder)[1]
                (folder/'12345678.route').write_text('not even valid labels')
                after = infer(folder)[1]
            self.assertEqual(before['predicted_arc_ids'],after['predicted_arc_ids'])
            self.assertFalse(any('reference' in key for key in after))

    def test_api_validation(self):
        from fastapi.testclient import TestClient
        from pathsnap.api import app
        client = TestClient(app)
        self.assertEqual(client.post('/predict',json={'trip_id':'../bad!!'}).status_code,400)
        self.assertEqual(client.post('/predict',json={'trip_id':'99999999'}).status_code,404)
        self.assertEqual(client.post('/predict',json={}).status_code,422)

if __name__ == '__main__': unittest.main()
