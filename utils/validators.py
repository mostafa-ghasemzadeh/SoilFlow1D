class InputValidator:
    @staticmethod
    def validate_soil_profile(layers):
        """Validate soil profile configuration"""
        errors = []
        
        if not layers:
            errors.append("At least one soil layer is required")
            return errors
        
        for i, layer in enumerate(layers):
            # Check thickness
            if layer.get('thickness', 0) <= 0:
                errors.append(f"Layer {i+1}: Thickness must be positive")
            
            # Check hydraulic parameters
            model = layer.get('hydraulic_model', 'van_genuchten')
            params = layer.get('hydraulic_params', {})
            
            if model == 'van_genuchten':
                if params.get('theta_r', 0) >= params.get('theta_s', 0):
                    errors.append(f"Layer {i+1}: θr must be less than θs") 
                if params.get('alpha', 0) <= 0:
                    errors.append(f"Layer {i+1}: α must be positive")
                if params.get('n', 1) <= 1:
                    errors.append(f"Layer {i+1}: n must be greater than 1")
                if params.get('Ks', 0) <= 0:
                    errors.append(f"Layer {i+1}: Ks must be positive")
            elif model == 'brooks_corey':
                if params.get('theta_r', 0) >= params.get('theta_s', 0):
                    errors.append(f"Layer {i+1}: θr must be less than θs")
                if params.get('hb', 0) <= 0:
                    errors.append(f"Layer {i+1}: hb must be positive")
                if params.get('lambda_bc', 0) <= 0:
                    errors.append(f"Layer {i+1}: λ must be positive")
                if params.get('Ks', 0) <= 0:
                    errors.append(f"Layer {i+1}: Ks must be positive")
        return errors

    @staticmethod
    def validate_simulation_settings(settings):
        """Validate simulation settings"""
        errors = []
        
        if settings.get('nodes_per_cm', 1) < 1:
            errors.append("Nodes per cm must be at least 1")
        
        if settings.get('dt_init', 0) <= 0:
            errors.append("Initial time step must be positive")
        
        if settings.get('dt_max', 0) <= 0:
            errors.append("Maximum time step must be positive")
        
        if settings.get('dt_init', 0) > settings.get('dt_max', 1):
            errors.append("Initial time step cannot exceed maximum time step")
        
        if settings.get('t_end', 0) <= 0:
            errors.append("Simulation end time must be positive")
        
        if settings.get('tolerance', 0) <= 0:
            errors.append("Tolerance must be positive")
        
        return errors

    @staticmethod
    def validate_boundary_conditions(bc_data):
        """Validate boundary conditions"""
        errors = []
        
        top_type = bc_data.get('top_type')
        if top_type == 'constant_head' and bc_data.get('top_head') is None:
            errors.append("Top boundary: Constant head value required")
        
        if top_type == 'constant_flux' and bc_data.get('top_flux') is None:
            errors.append("Top boundary: Constant flux value required")
        
        bottom_type = bc_data.get('bottom_type')
        if bottom_type == 'constant_head' and bc_data.get('bottom_head') is None:
            errors.append("Bottom boundary: Constant head value required")
        
        if bottom_type == 'constant_flux' and bc_data.get('bottom_flux') is None:
            errors.append("Bottom boundary: Constant flux value required")
        
        return errors

    @staticmethod
    def validate_time_series(time_series):
        """Validate time series data"""
        errors = []
        
        if not time_series:
            return errors
        
        prev_time = -1
        for i, entry in enumerate(time_series):
            time = entry.get('time')
            if time is None:
                errors.append(f"Row {i+1}: Time value required")
            elif time <= prev_time:
                errors.append(f"Row {i+1}: Time must be increasing")
            prev_time = time if time is not None else prev_time
        
        return errors
