"""Test getting/setting variables and subjacs with promoted/relative/absolute names."""

import unittest
import numpy as np
from openmdao.api import Problem, Group, ExecComp, IndepVarComp, DirectSolver, ParallelGroup, NewtonSolver
from openmdao.utils.mpi import MPI
from openmdao.utils.assert_utils import assert_near_equal, assert_warning
from openmdao.utils.om_warnings import OpenMDAOWarning
from openmdao.utils.testing_utils import use_tempdirs

try:
    from openmdao.vectors.petsc_vector import PETScVector
except ImportError:
    PETScVector = None


class TestGetSetVariables(unittest.TestCase):

    def test_no_promotion(self):
        """
        Illustrative examples showing how to access variables and subjacs.
        """
        c = ExecComp('y=2*x')

        g = Group()
        g.add_subsystem('c', c)

        model = Group()
        model.add_subsystem('g', g)

        p = Problem(model)
        p.setup()

        # -------------------------------------------------------------------

        # inputs
        p['g.c.x'] = 5.0
        self.assertEqual(p['g.c.x'], 5.0)

        # outputs
        p['g.c.y'] = 5.0
        self.assertEqual(p['g.c.y'], 5.0)

        # Conclude setup but don't run model.
        p.final_setup()

        inputs, outputs, residuals = g.get_nonlinear_vectors()

        # inputs
        inputs['c.x'] = 5.0
        self.assertEqual(inputs['c.x'], 5.0)

        # outputs
        outputs['c.y'] = 5.0
        self.assertEqual(outputs['c.y'], 5.0)

        # Removed part of test where we set values into the jacobian willy-nilly.
        # You can only set declared values now.

    def test_with_promotion(self):
        """
        Illustrative examples showing how to access variables and subjacs.
        """
        c1 = IndepVarComp('x')
        c2 = ExecComp('y=2*x')
        c3 = ExecComp('z=3*x')

        g = Group()
        g.add_subsystem('c1', c1, promotes=['*'])
        g.add_subsystem('c2', c2, promotes=['*'])
        g.add_subsystem('c3', c3, promotes=['*'])

        model = Group()
        model.add_subsystem('g', g, promotes=['*'])

        p = Problem(model)
        p.setup()

        # -------------------------------------------------------------------

        # inputs
        p['g.c2.x'] = 5.0
        self.assertEqual(p['g.c2.x'], 5.0)

        # outputs
        p['g.c2.y'] = 5.0
        self.assertEqual(p['g.c2.y'], 5.0)
        p['y'] = 5.0
        self.assertEqual(p['y'], 5.0)

        # Conclude setup but don't run model.
        p.final_setup()

        inputs, outputs, residuals = g.get_nonlinear_vectors()

        # inputs
        inputs['c2.x'] = 5.0
        self.assertEqual(inputs['c2.x'], 5.0)

        # outputs
        outputs['c2.y'] = 5.0
        self.assertEqual(outputs['c2.y'], 5.0)
        outputs['y'] = 5.0
        self.assertEqual(outputs['y'], 5.0)

        # Removed part of test where we set values into the jacobian willy-nilly. You can only set
        # declared values now.

    def test_no_promotion_errors(self):
        """
        Tests for error-handling for invalid variable names and keys.
        """
        p = Problem()
        model = p.model
        g = model.add_subsystem('g', Group(assembled_jac_type='dense'))
        g.linear_solver = DirectSolver(assemble_jac=True)
        # add a NewtonSolver so run_model will initialize Group g's jacobian.
        g.nonlinear_solver = NewtonSolver(solve_subsystems=False)
        g.add_subsystem('c', ExecComp('y=2*x'))
        p.setup()

        # -------------------------------------------------------------------

        msg = "<model> <class Group>: Variable '{}' not found. Perhaps you meant one of the following variables: ['g.c.{}']."

        # inputs
        with self.assertRaises(KeyError) as ctx:
            p['x'] = 5.0
        self.assertEqual(ctx.exception.args[0], msg.format('x', 'x'))

        with self.assertRaises(KeyError) as ctx:
            p['x']
        self.assertEqual(ctx.exception.args[0], msg.format('x', 'x'))

        # outputs
        with self.assertRaises(KeyError) as ctx:
            p['y'] = 5.0
        self.assertEqual(ctx.exception.args[0], msg.format('y', 'y'))

        with self.assertRaises(KeyError) as ctx:
            p['y']
        self.assertEqual(ctx.exception.args[0], msg.format('y', 'y'))

        p.final_setup()

        msg = "'g' <class Group>: Variable name '{}' not found."
        inputs, outputs, residuals = g.get_nonlinear_vectors()

        # inputs
        with self.assertRaises(KeyError) as cm:
           inputs['x'] = 5.0
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'x' not found.")

        with self.assertRaises(KeyError) as cm:
           inputs['x']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'x' not found. Perhaps you meant one of the following variables: ['c.x'].")

        with self.assertRaises(KeyError) as cm:
           inputs['g.c.x'] = 5.0
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c.x' not found.")

        with self.assertRaises(KeyError) as cm:
           inputs['g.c.x']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c.x' not found. Perhaps you meant one of the following variables: ['c.x', 'c.y'].")

        p.run_model()

        # outputs
        with self.assertRaises(KeyError) as cm:
           outputs['y'] = 5.0
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'y' not found.")

        with self.assertRaises(KeyError) as cm:
           outputs['y']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'y' not found. Perhaps you meant one of the following variables: ['c.y'].")

        with self.assertRaises(KeyError) as cm:
           outputs['g.c.y'] = 5.0
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c.y' not found.")

        with self.assertRaises(KeyError) as cm:
           outputs['g.c.y']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c.y' not found. Perhaps you meant one of the following variables: ['c.x', 'c.y'].")

        msg = "DenseJacobian in 'g'<class Group>: Variable name pair {} not found."
        jac = g.linear_solver._assembled_jac

        # d(output)/d(input)
        with self.assertRaises(KeyError) as cm:
            jac['y', 'x'] = 5.0
        self.assertEqual(cm.exception.args[0], "Variable name pair ('y', 'x') not found.")
        with self.assertRaises(KeyError) as cm:
            jac['y', 'x']
        self.assertEqual(cm.exception.args[0], "Variable name pair ('y', 'x') not found.")

        # d(output)/d(output)
        with self.assertRaises(KeyError) as cm:
            jac['y', 'y'] = 5.0
        self.assertEqual(cm.exception.args[0], "Variable name pair ('y', 'y') not found.")
        with self.assertRaises(KeyError) as cm:
            jac['y', 'y']
        self.assertEqual(cm.exception.args[0], "Variable name pair ('y', 'y') not found.")


    def test_with_promotion_errors(self):
        """
        Tests for error-handling for invalid variable names and keys.
        """
        g = Group(assembled_jac_type='dense')
        g.add_subsystem('c1', IndepVarComp('x'), promotes=['*'])
        g.add_subsystem('c2', ExecComp('y=2*x'), promotes=['*'])
        g.add_subsystem('c3', ExecComp('z=3*x'), promotes=['*'])
        g.linear_solver = DirectSolver(assemble_jac=True)

        model = Group()
        model.add_subsystem('g', g, promotes=['*'])

        p = Problem(model)
        p.setup()

        # Conclude setup but don't run model.
        p.final_setup()

        g._get_jacobian()

        # -------------------------------------------------------------------

        msg1 = "'g' <class Group>: Variable name '{}' not found."
        msg2 = "'g' <class Group>: The promoted name x is invalid because it refers to multiple inputs: " \
               "[g.c2.x ,g.c3.x]. Access the value from the connected output variable x instead."

        inputs, outputs, residuals = g.get_nonlinear_vectors()

        # inputs
        with self.assertRaises(Exception) as context:
            inputs['x'] = 5.0
        self.assertEqual(str(context.exception), msg2)
        with self.assertRaises(Exception) as context:
            self.assertEqual(inputs['x'], 5.0)
        self.assertEqual(str(context.exception), msg2)

        with self.assertRaises(KeyError) as cm:
            inputs['g.c2.x'] = 5.0
        self.assertEqual(cm.exception.args[0], msg1.format('g.c2.x'))

        with self.assertRaises(KeyError) as cm:
            inputs['g.c2.x']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c2.x' not found. Perhaps you meant one of the following variables: ['x'].")

        # outputs
        with self.assertRaises(KeyError) as cm:
            outputs['g.c2.y'] = 5.0
        self.assertEqual(cm.exception.args[0], msg1.format('g.c2.y'))

        with self.assertRaises(KeyError) as cm:
            outputs['g.c2.y']
        self.assertEqual(cm.exception.args[0], "'g' <class Group>: Variable name 'g.c2.y' not found. Perhaps you meant one of the following variables: ['y'].")

        msg1 = r'Variable name pair \("{}", "{}"\) not found.'

        jac = g.linear_solver._assembled_jac

        # d(outputs)/d(inputs)
        with self.assertRaises(Exception) as context:
            jac['y', 'x'] = 5.0
        self.assertEqual(context.exception.args[0], msg2)

        with self.assertRaises(Exception) as context:
            self.assertEqual(jac['y', 'x'], 5.0)
        self.assertEqual(str(context.exception), msg2)

    def test_serial_multi_src_inds(self):
        p = Problem()
        p.model.add_subsystem('indep', IndepVarComp('x', val=np.ones(10)))
        p.model.add_subsystem('C1', ExecComp('y=x*2.', x=np.zeros(7), y=np.zeros(7)))
        p.model.add_subsystem('C2', ExecComp('y=x*3.', x=np.zeros(3), y=np.zeros(3)))
        p.model.connect('indep.x', 'C1.x', src_indices=list(range(7)))
        p.model.connect('indep.x', 'C2.x', src_indices=list(range(7, 10)))
        p.setup()

        p['C1.x'] = (np.arange(7) + 1.) * 2.
        p['C2.x'] = (np.arange(7,10) + 1.) * 3.

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['indep.x'][7:10], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['C1.x'], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['C2.x'], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['C1.y'], (np.arange(7) + 1.) * 4.)
        np.testing.assert_allclose(p['C2.y'], (np.arange(7,10) + 1.) * 9.)

    def test_serial_multi_src_inds_promoted(self):
        p = Problem()
        p.model.add_subsystem('indep', IndepVarComp('x', val=np.ones(10)), promotes=['x'])
        p.model.add_subsystem('C1', ExecComp('y=x*2.',
                                             x={'val': np.zeros(7)},
                                             y={'val': np.zeros(7)}))
        p.model.add_subsystem('C2', ExecComp('y=x*3.',
                                             x={'val': np.zeros(3)},
                                             y={'val': np.zeros(3)}))

        p.model.promotes('C1', inputs=['x'], src_indices=list(range(7)))
        p.model.promotes('C2', inputs=['x'], src_indices=list(range(7, 10)))

        p.setup()

        p['C1.x'] = (np.arange(7) + 1.) * 2.
        p['C2.x'] = (np.arange(7,10) + 1.) * 3.

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['indep.x'][7:10], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['C1.x'], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['C2.x'], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['C1.y'], (np.arange(7) + 1.) * 4.)
        np.testing.assert_allclose(p['C2.y'], (np.arange(7,10) + 1.) * 9.)

    def test_serial_multi_src_inds_units_promoted(self):
        p = Problem()
        indep = p.model.add_subsystem('indep', IndepVarComp(), promotes=['x'])
        indep.add_output('x', units='inch', val=np.ones(10))
        p.model.add_subsystem('C1', ExecComp('y=x*2.',
                                             x={'val': np.zeros(7),
                                                'units': 'ft'},
                                             y={'val': np.zeros(7), 'units': 'ft'}))
        p.model.add_subsystem('C2', ExecComp('y=x*3.',
                                             x={'val': np.zeros(3),
                                                'units': 'inch'},
                                             y={'val': np.zeros(3), 'units': 'inch'}))

        p.model.promotes('C1', inputs=['x'], src_indices=list(range(7)))
        p.model.promotes('C2', inputs=['x'], src_indices=list(range(7, 10)))

        p.setup()

        p['C1.x'] = np.ones(7) * 2.
        p['C2.x'] = np.ones(3) * 3.

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], np.ones(7) * 24.)
        np.testing.assert_allclose(p['indep.x'][7:10], np.ones(3) * 3.)
        np.testing.assert_allclose(p['C1.x'], np.ones(7) * 2.)
        np.testing.assert_allclose(p['C1.y'], np.ones(7) * 4.)
        np.testing.assert_allclose(p['C2.x'], np.ones(3) * 3.)
        np.testing.assert_allclose(p['C2.y'], np.ones(3) * 9.)

    def test_serial_multi_src_inds_units_promoted_no_src(self):
        p = Problem(name='serial_multi_src_inds_units_promoted_no_src')
        p.model.add_subsystem('C1', ExecComp('y=x*2.',
                                             x={'val': np.zeros(7),
                                                'units': 'ft'},
                                             y={'val': np.zeros(7), 'units': 'ft'}))
        p.model.add_subsystem('C2', ExecComp('y=x*3.',
                                             x={'val': np.zeros(3),
                                                'units': 'inch'},
                                             y={'val': np.zeros(3), 'units': 'inch'}))
        p.model.add_subsystem('C3', ExecComp('y=x*4.',
                                             x={'val': np.zeros(10), 'units': 'mm'},
                                             y={'val': np.zeros(10), 'units': 'mm'}),
                         promotes=['x'])

        p.model.promotes('C1', inputs=['x'], src_indices=list(range(7)))
        p.model.promotes('C2', inputs=['x'], src_indices=list(range(7, 10)))

        with self.assertRaises(RuntimeError) as cm:
            p.setup()
            p.final_setup()

        self.assertEqual(str(cm.exception),
           "\nCollected errors for problem 'serial_multi_src_inds_units_promoted_no_src':"
           "\n   <model> <class Group>: The following inputs, ['C1.x', 'C2.x', 'C3.x'], promoted "
           "to 'x', are connected but their metadata entries ['units'] differ. Call "
           "<group>.set_input_defaults('x', units=?), where <group> is the model to remove the ambiguity.")

    def test_serial_multi_src_inds_units_setval_promoted(self):
        p = Problem()
        indep = p.model.add_subsystem('indep', IndepVarComp(), promotes=['x'])
        indep.add_output('x', units='inch', val=np.ones(10))
        p.model.add_subsystem('C1', ExecComp('y=x*2.',
                                             x={'val': np.zeros(7),
                                                'units': 'ft'},
                                             y={'val': np.zeros(7), 'units': 'ft'}))
        p.model.add_subsystem('C2', ExecComp('y=x*3.',
                                             x={'val': np.zeros(3),
                                                'units': 'inch'},
                                             y={'val': np.zeros(3), 'units': 'inch'}))

        p.model.promotes('C1', inputs=['x'], src_indices=list(range(7)))
        p.model.promotes('C2', inputs=['x'], src_indices=list(range(7, 10)))

        p.setup()

        p.set_val('C1.x', np.ones(7) * 24., units='inch')
        p.set_val('C2.x', np.ones(3) * 3., units='inch')

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], np.ones(7) * 24.)
        np.testing.assert_allclose(p['indep.x'][7:10], np.ones(3) * 3.)
        np.testing.assert_allclose(p['C1.x'], np.ones(7) * 2.)
        np.testing.assert_allclose(p['C1.y'], np.ones(7) * 4.)
        np.testing.assert_allclose(p['C2.x'], np.ones(3) * 3.)
        np.testing.assert_allclose(p['C2.y'], np.ones(3) * 9.)


@unittest.skipUnless(MPI and PETScVector, "MPI and PETSc are required.")
@use_tempdirs
class ParTestCase(unittest.TestCase):
    N_PROCS = 2

    def test_par_multi_src_inds(self):
        p = Problem()
        p.model.add_subsystem('indep', IndepVarComp('x', val=np.ones(10)))
        par = p.model.add_subsystem('par', ParallelGroup())
        par.add_subsystem('C1', ExecComp('y=x*2.', x=np.zeros(7), y=np.zeros(7)))
        par.add_subsystem('C2', ExecComp('y=x*3.', x=np.zeros(3), y=np.zeros(3)))
        p.model.connect('indep.x', 'par.C1.x', src_indices=list(range(7)))
        p.model.connect('indep.x', 'par.C2.x', src_indices=list(range(7, 10)))

        p.setup()

        p['indep.x'] = np.concatenate([(np.arange(7) + 1.) * 2., (np.arange(7, 10) + 1.) * 3.])

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['indep.x'][7:10], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p.get_val('par.C1.x', get_remote=True), (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p.get_val('par.C2.x', get_remote=True), (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p.get_val('par.C1.y', get_remote=True), (np.arange(7) + 1.) * 4.)
        np.testing.assert_allclose(p.get_val('par.C2.y', get_remote=True), (np.arange(7,10) + 1.) * 9.)

    @unittest.expectedFailure
    def test_par_multi_src_inds_fail(self):
        p = Problem()
        p.model.add_subsystem('indep', IndepVarComp('x', val=np.ones(10)))
        par = p.model.add_subsystem('par', ParallelGroup())
        par.add_subsystem('C1', ExecComp('y=x*2.', x=np.zeros(7), y=np.zeros(7)))
        par.add_subsystem('C2', ExecComp('y=x*3.', x=np.zeros(3), y=np.zeros(3)))
        p.model.connect('indep.x', 'par.C1.x', src_indices=list(range(7)))
        p.model.connect('indep.x', 'par.C2.x', src_indices=list(range(7, 10)))

        p.setup()

        p['par.C1.x'] = (np.arange(7) + 1.) * 2.
        p['par.C2.x'] = (np.arange(7,10) + 1.) * 3.

        p.run_model()

        np.testing.assert_allclose(p['indep.x'][:7], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['indep.x'][7:10], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['par.C1.x'], (np.arange(7) + 1.) * 2.)
        np.testing.assert_allclose(p['par.C2.x'], (np.arange(7,10) + 1.) * 3.)
        np.testing.assert_allclose(p['par.C1.y'], (np.arange(7) + 1.) * 4.)
        np.testing.assert_allclose(p['par.C2.y'], (np.arange(7,10) + 1.) * 9.)

    def test_load_case_remote_input_src_indices(self):
        import numpy as np
        import openmdao.api as om
        from openmdao.utils.assert_utils import assert_near_equal

        p = om.Problem()

        class CompA(om.ExplicitComponent):

            def setup(self):
                self.add_input('x', shape=(5,))
                self.add_output('y', shape=(5,))

            def compute(self, inputs, outputs):
                outputs['y'] = inputs['x']

        class CompB(om.ExplicitComponent):

            def setup(self):
                self.add_input('y', shape=(1,))
                self.add_output('z', shape=(1,))

            def compute(self, inputs, outputs):
                outputs['z'] = inputs['y']

        p.add_recorder(om.SqliteRecorder('load_case_issue.sql'))
        p.recording_options['record_inputs'] = True
        p.recording_options['record_outputs'] = True

        G = p.model.add_subsystem('G', om.ParallelGroup())

        a = G.add_subsystem('a', CompA())
        G.add_subsystem('b', CompB())

        G.connect('a.y', 'b.y', src_indices=[-1])

        G.nonlinear_solver = om.NonlinearBlockJac(iprint=2)
        G.linear_solver = om.PETScKrylov(iprint=2)

        p.setup()

        if a in G._subsystems_myproc:
            p.set_val('G.a.x', np.linspace(0, np.pi, 5))

        p.run_model()

        p.record(case_name='case_1')
        p.cleanup()

        p.comm.barrier()

        case_1 = om.CaseReader(p.get_outputs_dir() / 'load_case_issue.sql').get_case('case_1')
        assert_near_equal(case_1.get_val('G.a.y')[-1], case_1.get_val('G.b.y'))

        # Populate the x input with zeros just to make sure we're changing it.
        p.set_val('G.a.x', 0.0)
        p.run_model()

        # Try to load the case into the model. This should trigger the following warning.
        expected_warning = "<model> <class Group>: Cannot set the value of 'G.b.y': " \
                           "Setting the value of a remote connected input with src_indices " \
                           "is currently not supported, you must call `run_model()` to have " \
                           "the outputs populate their corresponding inputs."
        with assert_warning(OpenMDAOWarning, expected_warning, ranks=0):
            p.load_case(case_1)


class SystemSetValTestCase(unittest.TestCase):
    def setup_model(self):
        p = Problem()
        model = p.model
        G1 = model.add_subsystem('G1', Group())
        G2 = G1.add_subsystem('G2', Group())
        C1 = G2.add_subsystem('C1', ExecComp('y=2*x'))

        p.setup()
        return p, G1, G2, C1

    def test_set_val(self):
        p, G1, G2, C1 = self.setup_model()
        C1.set_val('x', 42.)
        G2.set_val('C1.x', 99.)

        assert_near_equal(p['G1.G2.C1.x'], 99.)

        p.final_setup()

        assert_near_equal(p['G1.G2.C1.x'], 99.)

    def test_set_val2(self):
        p, G1, G2, C1 = self.setup_model()
        G2.set_val('C1.x', 99.)
        C1.set_val('x', 42.)

        assert_near_equal(p['G1.G2.C1.x'], 42.)

        p.final_setup()

        assert_near_equal(p['G1.G2.C1.x'], 42.)


if __name__ == '__main__':
    unittest.main()
