from sympy import Array as _Array


from ..geometry_map import GeometryMap
class ParametricSurface(GeometryMap):
    
    def __init__(self, exprs, syms):
        GeometryMap.__init__(self, exprs, syms)
    def subs(self, subs_arg):
        return ParametricSurface(self._exprs.subs(subs_arg), self._syms)

    def chain(self, other):
        from ..geometry_map.coord_transform import CoordTransform

        assert( len(other.sym()) == int(self.expr().shape.args[0]) )
        
        if isinstance(other, CoordTransform):
            return ParametricSurface(other._exprs.subs({
                other.sym(i): self.expr(i) for i in range(len(self.sym()))}), 
                self._syms)
        else:
            raise TypeError("The chain succession must be a GeometryMap.")
    def __or__(self, other):
        return self.chain(other)

    # def __str__(self):
    #     return f"A surface = {self.expr()}, with {self.u} domain {self._u_limit}, {self.v} domain {self._v_limit}."

    # 1-form, ds^2 = Edu^2 + 2Fdudv + Gdv^2
    # dA = |\vec{r}_u x \vec{r}_v |  differential area 
    def E_F_G(self): 
        from silkpy.sympy_utility import dot
        r_u = self.expr().diff(self.sym(0))
        r_v = self.expr().diff(self.sym(1))
        return dot(r_u, r_u), dot(r_u, r_v), dot(r_v, r_v)
    def metric_tensor(self):
        from einsteinpy.symbolic import MetricTensor
        E, F, G = self.E_F_G()
        return MetricTensor([[E, F], [F, G]], self.sym(), config='ll')
            
    def normal_vector(self):
        from silkpy.sympy_utility import cross, norm
        from einsteinpy.symbolic.vector import GenericVector
        r_u = self.expr().diff(self.sym(0))
        r_v = self.expr().diff(self.sym(1))
        r_u_x_r_v = cross(r_u, r_v)
        # cross product of r_u and r_v
        return r_u_x_r_v / norm(r_u_x_r_v)

    # 2-form, 2\delta = L du^2 + 2M dudv + N dv^2
    def L_M_N(self):
        from silkpy.sympy_utility import dot
        n = self.normal_vector()
        r_uu = self.expr().diff(self.sym(0), 2)
        r_uv = self.expr().diff(self.sym(0), self.sym(1))
        r_vv = self.expr().diff(self.sym(1), 2)
        return dot(r_uu, n), dot(r_uv, n), dot(r_vv, n)
    def Omega(self):
        from einsteinpy.symbolic.tensor import BaseRelativityTensor
        L, M, N = self.L_M_N()
        return BaseRelativityTensor(
                    [[L, M], [M, N]], 
                    self.sym(), 
                    config='ll', 
                    parent_metric=self.metric_tensor() # TODO: check the metric.
                )
        
    def christoffel_symbol(self):
        from einsteinpy.symbolic import ChristoffelSymbols
        return ChristoffelSymbols.from_metric(self.metric_tensor())
    def riemann_curvature_tensor(self):
        from einsteinpy.symbolic import RiemannCurvatureTensor
        return RiemannCurvatureTensor.from_christoffels(self.christoffel_symbol())

    # \omega^m_k = \sum_{i} g^{mi} \Omega_{ik}
    def weingarten_matrix(self):
        from einsteinpy.symbolic.tensor import tensor_product
        from sympy import Matrix
        return Matrix(tensor_product( 
            self.metric_tensor().change_config('uu'), 
            self.Omega(), i=1,j=0).tensor())
    def weingarten_transform(self, vec):
        """
        Args:
        v: planar vector in tangent plane, which would be decomposed into r_u and r_v.
        """
        from sympy.solvers.solveset import linsolve
        from sympy import Matrix, symbols
        r_u = self.expr().diff(self.sym(0))
        r_v = self.expr().diff(self.sym(1))

        c_ru, c_rv = symbols('c_ru, c_rv', real=True)
        solset = linsolve(Matrix(
            ((r_u[0], r_v[0], vec[0]), 
             (r_u[1], r_v[1], vec[1]), 
             (r_u[2], r_v[2], vec[2]))), (c_ru, c_rv))
        try:    
            if len(solset) != 1:
                raise RuntimeError(f"Sympy is not smart enough to decompose the v vector with r_u, r_v as the basis.\
                It found these solutions: {solset}.\
                Users need to choose from them or deduce manually, and then set it by arguments.")
        except:
            raise RuntimeError("We failed to decompose the input vec into r_u and r_v")
        else:
            c_ru, c_rv = next(iter(solset))
        omega = self.weingarten_matrix()
        W_r_u = omega[0, 0] * r_u + omega[1, 0] * r_v
        W_r_v = omega[0, 1] * r_u + omega[1, 1] * r_v
        return c_ru * W_r_u + c_rv * W_r_v

    # total curvature K = det(w^i_j)
    # average curvature H = 1/2 * Tr(w^i_j)
    def K_H(self):
        w = self.weingarten_matrix()
        return w[0,0] * w[1,1] - w[0,1] * w[1,0], (w[0,0] + w[1,1]) / 2
    
    def prin_curvature_and_vector(self):
        from silkpy.sympy_utility import norm
        w = self.weingarten_matrix()
        r_u = self.expr().diff(self.sym(0))
        r_v = self.expr().diff(self.sym(1))

        eigen = w.eigenvects()

        if eigen[0][1] == 2: # if the two eigenvalues are identical
            k1 = k2 = eigen[0][0]
            er1 = eigen[0][2][0][0] * r_u +  eigen[0][2][0][1] * r_v
            e2 = e1 = er1 / norm(er1)
        else:
            k1 = eigen[0][0]
            k2 = eigen[1][0]
            er1 = eigen[0][2][0][0] * r_u +  eigen[0][2][0][1] * r_v
            e1 = er1 / norm(er1)
            er2 = eigen[1][2][0][0] * r_u +  eigen[1][2][0][1] * r_v
            e2 = er2 / norm(er2)
        return (k1, e1), (k2, e2)
        
